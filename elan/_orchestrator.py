from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from ._activation import Activation
from ._binding import bind_output
from ._branch import Branch
from ._context import copy_context, prepare_context
from ._expansion import materialize_expansion
from ._join_activation import JoinActivation
from ._join_state import JoinInstance, JoinState
from ._refs import RefLookup
from ._resolution import resolve_node
from ._routing import (
    ResolvedNext,
    is_target_producer_list,
    resolve_next_targets,
)
from ._run_state import RunState
from ._scheduler import Scheduler
from .expand import Expand, _BoundExpand
from .join import Join
from .result import WorkflowRun


RunnableActivation = Activation | JoinActivation


class Orchestrator:
    def __init__(
        self,
        *,
        run_state: RunState,
    ) -> None:
        self.run_state = run_state

    async def run(self, input_value: Any) -> WorkflowRun:
        scheduler = Scheduler(orchestrator=self)
        self._seed_run(scheduler, input_value)

        while True:
            settled = await self._next_settled_activation(scheduler)
            if settled is None:
                completed = self._complete_run_or_schedule_join(scheduler)
                if completed is not None:
                    return completed
                continue

            self._record_output(settled)
            self._enqueue_next_activations(scheduler, settled)

    def _seed_run(
        self,
        scheduler: Scheduler,
        input_value: dict[str, Any],
    ) -> None:
        initial_branch = self._create_branch(
            current_node_name="start",
            is_entry=True,
        )
        self.run_state.entry_branch_id = initial_branch.id
        initial_activation = self._create_activation(
            initial_branch,
            input_value=input_value,
        )
        scheduler.enqueue(initial_activation)
        self.run_state.mark_running()

    async def _next_settled_activation(
        self,
        scheduler: Scheduler,
    ) -> RunnableActivation | None:
        settled = scheduler.next_settled()
        if settled is not None:
            return settled
        return await scheduler.update()

    def _complete_run_or_schedule_join(
        self,
        scheduler: Scheduler,
    ) -> WorkflowRun | None:
        if not scheduler.is_quiescent():
            raise RuntimeError(
                f"Workflow '{self.run_state.workflow.name}' reached a non-quiescent "
                "state without queued activations."
            )

        if self._has_active_branches():
            raise RuntimeError(
                f"Workflow '{self.run_state.workflow.name}' reached quiescence with "
                "active branches."
            )

        result_join = self.run_state.join_states.get("result")
        if result_join is not None and result_join.scope_node_name is None:
            if not result_join.finalized:
                scheduler.enqueue(self._start_workflow_join(result_join))
                return None
        elif result_join is not None:
            if not result_join.instances:
                raise RuntimeError(
                    f"Workflow '{self.run_state.workflow.name}' terminal scoped Join "
                    f"'result' did not activate scope '{result_join.scope_node_name}'."
                )
            if not result_join.finalized:
                raise RuntimeError(
                    f"Workflow '{self.run_state.workflow.name}' terminal scoped Join "
                    "did not settle."
                )

        self.run_state.mark_completed()
        return WorkflowRun(
            result=self._final_result(),
            outputs=self.run_state.outputs,
            context=self._final_context(),
        )

    def activation_for_id(
        self,
        activation_id: str,
    ) -> RunnableActivation:
        return self.run_state.activations[activation_id]

    def context_for_activation(
        self,
        activation: RunnableActivation,
    ) -> Any:
        branch_context = self.run_state.context_for_branch(activation.branch_id)
        if isinstance(activation, JoinActivation):
            return branch_context

        lookup = RefLookup(
            workflow_input=self.run_state.workflow_input,
            context=branch_context,
            policy=self.run_state.policy,
            upstream_value=None if activation.is_entry else activation.input_value,
        )
        prepared_context = prepare_context(
            workflow_name=self.run_state.workflow.name,
            branch_context=branch_context,
            mapping=activation.node.context,
            lookup=lookup,
            phase_name="Node.context",
        )
        self.run_state.set_context_for_branch(activation.branch_id, prepared_context)
        return prepared_context

    def _enqueue_next_activations(
        self,
        scheduler: Scheduler,
        settled: RunnableActivation,
    ) -> None:
        if isinstance(settled, JoinActivation):
            next_activations = self._progress_join(settled)
        else:
            next_activations = self._progress_branch(settled)
        for next_activation in next_activations:
            scheduler.enqueue(next_activation)

    def handle_yielded_output(
        self,
        *,
        scheduler: Scheduler,
        activation: Activation,
        yielded_output: Any,
    ) -> None:
        next_activations = self._progress_yielded_output(
            activation,
            yielded_output,
        )
        for next_activation in next_activations:
            scheduler.enqueue(next_activation)
        scheduler.launch_ready()

    def _progress_branch(
        self,
        settled: Activation,
    ) -> list[RunnableActivation]:
        branch = self.run_state.branches[settled.branch_id]
        if settled.yielded:
            if settled.node.next is not None:
                self.run_state.mark_branching_used()
            return self._retire_branch(branch)

        emitted_value = bind_output(settled.node.bind_output, settled.output)
        if isinstance(settled.node.next, (Expand, _BoundExpand)):
            return self._create_expansion_activations(
                branch,
                emitted_value=emitted_value,
                site=settled.node.next,
                yielded=False,
            )
        if isinstance(settled.node.next, dict) or is_target_producer_list(
            settled.node.next
        ):
            self.run_state.mark_branching_used()

        if (
            is_target_producer_list(settled.node.next)
            and "result" in self.run_state.graph.nodes
            and not self._uses_join_result()
            and not branch.scope_instances
        ):
            raise NotImplementedError(
                "List-based branching with reserved result is not implemented before Join."
            )

        next_targets = resolve_next_targets(
            self.run_state.workflow.name,
            next_value=settled.node.next,
            route_on=settled.node.route_on,
            emitted_value=emitted_value,
            nodes=self.run_state.graph.nodes,
        )
        return self._create_next_activations(branch, emitted_value, next_targets)

    def _progress_join(
        self,
        settled: JoinActivation,
    ) -> list[RunnableActivation]:
        join_state = self.run_state.join_states[settled.node_name]
        join_instance = join_state.instances[settled.join_instance_id]
        join_instance.status = "settled"
        if settled.node_name == "result":
            join_state.finalized = True

        branch = self.run_state.branches[settled.branch_id]
        emitted_value = bind_output(settled.join.bind_output, settled.output)
        if isinstance(settled.join.next, (Expand, _BoundExpand)):
            return self._create_expansion_activations(
                branch,
                emitted_value=emitted_value,
                site=settled.join.next,
                yielded=False,
            )
        if isinstance(settled.join.next, dict) or is_target_producer_list(
            settled.join.next
        ):
            self.run_state.mark_branching_used()

        next_targets = resolve_next_targets(
            self.run_state.workflow.name,
            next_value=settled.join.next,
            route_on=settled.join.route_on,
            emitted_value=emitted_value,
            nodes=self.run_state.graph.nodes,
        )
        return self._create_next_activations(branch, emitted_value, next_targets)

    def _progress_yielded_output(
        self,
        activation: Activation,
        yielded_output: Any,
    ) -> list[RunnableActivation]:
        branch = self.run_state.branches[activation.branch_id]
        emitted_value = bind_output(activation.node.bind_output, yielded_output)

        if activation.node.next is not None:
            self.run_state.mark_branching_used()

        if isinstance(activation.node.next, (Expand, _BoundExpand)):
            return self._create_expansion_activations(
                branch,
                emitted_value=emitted_value,
                site=activation.node.next,
                yielded=True,
            )

        if (
            activation.node.next is not None
            and "result" in self.run_state.graph.nodes
            and not self._uses_join_result()
            and not branch.scope_instances
        ):
            raise NotImplementedError(
                "Yield-based branching with reserved result is not implemented before Join."
            )

        next_targets = resolve_next_targets(
            self.run_state.workflow.name,
            next_value=activation.node.next,
            route_on=activation.node.route_on,
            emitted_value=emitted_value,
            nodes=self.run_state.graph.nodes,
        )
        if next_targets is None:
            return []

        targets = next_targets if isinstance(next_targets, list) else [next_targets]
        activations: list[RunnableActivation] = []
        for next_name, _next_node in targets:
            if self._is_join_target(next_name):
                self._register_join_contribution(
                    branch,
                    join_node_name=next_name,
                    emitted_value=emitted_value,
                )
                continue
            child_branch = self._create_branch(
                current_node_name=next_name,
                is_entry=False,
                parent_branch_id=branch.id,
            )
            activations.append(
                self._create_activation(
                    child_branch,
                    input_value=emitted_value,
                )
            )
        return activations

    def _create_expansion_activations(
        self,
        branch: Branch,
        *,
        emitted_value: Any,
        site: Expand | _BoundExpand,
        yielded: bool,
    ) -> list[RunnableActivation]:
        materialized = materialize_expansion(
            self.run_state,
            site,
            emitted_value,
        )
        self.run_state.graph.nodes.update(materialized.nodes)
        self.run_state.join_states.update(materialized.join_states)

        if yielded:
            fragment_branch = self._create_branch(
                current_node_name=materialized.entry_name,
                is_entry=False,
                parent_branch_id=branch.id,
            )
        else:
            branch.advance_to(materialized.entry_name)
            fragment_branch = branch

        return [
            self._create_activation(
                fragment_branch,
                input_value=emitted_value,
            )
        ]

    def _record_output(
        self,
        activation: RunnableActivation,
    ) -> None:
        if isinstance(activation, Activation) and activation.context_output is not None:
            self.run_state.set_context_for_branch(
                activation.branch_id,
                activation.context_output,
            )

        self.run_state.last_output = activation.output
        self.run_state.last_branch_id = activation.branch_id
        if isinstance(activation, JoinActivation):
            if activation.reducer is not None:
                branch_outputs = self.run_state.outputs.setdefault(
                    activation.branch_id, {}
                )
                branch_outputs.setdefault(activation.reducer.name, []).append(
                    activation.output
                )
            if activation.node_name == "result":
                self.run_state.result = activation.output
            return

        branch_outputs = self.run_state.outputs.setdefault(activation.branch_id, {})
        branch_outputs.setdefault(activation.node.run.name, []).append(activation.output)
        if activation.node_name == "result":
            self.run_state.result = activation.output

    def _final_result(self) -> Any:
        if self.run_state.result is not None:
            return self.run_state.result
        if self.run_state.used_branching:
            return None
        return self.run_state.last_output

    def _create_next_activations(
        self,
        branch: Branch,
        emitted_value: Any,
        next_targets: ResolvedNext,
    ) -> list[RunnableActivation]:
        if next_targets is None:
            return self._retire_branch(branch)

        if not isinstance(next_targets, list):
            next_name, _next_node = next_targets
            if self._is_join_target(next_name):
                self._register_join_contribution(
                    branch,
                    join_node_name=next_name,
                    emitted_value=emitted_value,
                )
                return self._retire_branch(branch)

            branch.advance_to(next_name)
            return [
                self._create_activation(
                    branch,
                    input_value=emitted_value,
                )
            ]

        activations: list[RunnableActivation] = []
        for next_name, _next_node in next_targets:
            if self._is_join_target(next_name):
                self._register_join_contribution(
                    branch,
                    join_node_name=next_name,
                    emitted_value=emitted_value,
                )
                continue
            child_branch = self._create_branch(
                current_node_name=next_name,
                is_entry=False,
                parent_branch_id=branch.id,
            )
            activations.append(
                self._create_activation(
                    child_branch,
                    input_value=emitted_value,
                )
            )
        activations.extend(self._retire_branch(branch))
        return activations

    def _register_join_contribution(
        self,
        branch: Branch,
        *,
        join_node_name: str,
        emitted_value: Any,
    ) -> None:
        join_state = self.run_state.join_states[join_node_name]
        if join_state.is_workflow_scoped:
            join_state.workflow_contributions.append(emitted_value)
            return

        instance_id = branch.scope_instances.get(join_node_name)
        if instance_id is None:
            raise RuntimeError(
                f"Workflow '{self.run_state.workflow.name}' branch reached scoped Join "
                f"'{join_node_name}' without active scope '{join_state.scope_node_name}'."
            )
        if next(reversed(branch.scope_instances)) != join_node_name:
            raise RuntimeError(
                f"Workflow '{self.run_state.workflow.name}' branch reached Join "
                f"'{join_node_name}' before its nested scope was closed."
            )
        join_state.instances[instance_id].contributions.append(emitted_value)

    def _retire_branch(self, branch: Branch) -> list[JoinActivation]:
        owned_instances: list[tuple[str, JoinInstance]] = []
        for join_name, instance_id in branch.scope_instances.items():
            instance = self.run_state.join_states[join_name].instances[instance_id]
            if instance.owner_branch_id == branch.id and instance.status == "open":
                owned_instances.append((join_name, instance))

        if owned_instances:
            _join_name, owned_instance = owned_instances[-1]
            owned_instance.active_branch_ids.discard(branch.id)
            branch.suspend(owned_instance.id)
        else:
            for join_name, instance_id in tuple(branch.scope_instances.items()):
                instance = self.run_state.join_states[join_name].instances[instance_id]
                instance.active_branch_ids.discard(branch.id)
            branch.scope_instances.clear()
            branch.complete()

        return self._start_ready_join_activations()

    def _start_ready_join_activations(self) -> list[JoinActivation]:
        ready: list[JoinActivation] = []
        for join_name, join_state in self.run_state.join_states.items():
            if join_state.is_workflow_scoped:
                continue
            for join_instance in join_state.instances.values():
                if join_instance.status != "open" or join_instance.active_branch_ids:
                    continue
                join_instance.status = "reducing"
                owner = self.run_state.branches[join_instance.owner_branch_id]
                active_instance_id = owner.scope_instances.get(join_name)
                if (
                    active_instance_id != join_instance.id
                    or owner.suspended_on != join_instance.id
                ):
                    raise RuntimeError(
                        f"Workflow '{self.run_state.workflow.name}' lost owner scope "
                        f"for Join '{join_name}'."
                    )
                owner.scope_instances.pop(join_name)
                owner.advance_to(join_name)
                ready.append(
                    self._create_join_activation(
                        join_name=join_name,
                        join_instance=join_instance,
                    )
                )
        return ready

    def _start_workflow_join(self, join_state: JoinState) -> JoinActivation:
        if self.run_state.entry_branch_id is None:
            raise RuntimeError("Cannot start workflow Join without an entry branch.")
        owner = self.run_state.branches[self.run_state.entry_branch_id]
        self.run_state.set_context_for_branch(
            owner.id,
            copy_context(self.run_state.context),
        )
        owner.advance_to(join_state.node_name)
        instance = JoinInstance(
            id=f"{join_state.node_name}:workflow",
            scope_activation_id="workflow",
            owner_branch_id=owner.id,
            status="reducing",
            contributions=list(join_state.workflow_contributions),
        )
        join_state.instances[instance.id] = instance
        return self._create_join_activation(
            join_name=join_state.node_name,
            join_instance=instance,
        )

    def _open_join_scopes(
        self,
        activation: Activation,
        branch: Branch,
    ) -> None:
        if activation.node_name is None:
            return
        for join_name, join_state in self.run_state.join_states.items():
            if join_state.scope_node_name != activation.node_name:
                continue
            if join_name in branch.scope_instances:
                raise RuntimeError(
                    f"Workflow '{self.run_state.workflow.name}' cannot re-enter Join "
                    f"scope '{join_state.scope_node_name}' before its previous instance settled."
                )
            if join_name == "result" and join_state.instances:
                raise RuntimeError(
                    f"Workflow '{self.run_state.workflow.name}' terminal scoped Join "
                    "'result' was activated more than once."
                )

            instance = JoinInstance(
                id=f"{join_name}:{activation.id}",
                scope_activation_id=activation.id,
                owner_branch_id=branch.id,
                active_branch_ids={branch.id},
            )
            join_state.instances[instance.id] = instance
            branch.scope_instances[join_name] = instance.id

    def _is_join_target(self, node_name: str) -> bool:
        return node_name in self.run_state.join_states

    def _uses_join_result(self) -> bool:
        return "result" in self.run_state.join_states

    def _has_active_branches(self) -> bool:
        return any(
            not branch.is_complete for branch in self.run_state.branches.values()
        )

    def _final_context(self) -> BaseModel | None:
        result_join = self.run_state.join_states.get("result")
        if result_join is not None and result_join.finalized:
            result_instance = next(iter(result_join.instances.values()))
            return self.run_state.context_for_branch(result_instance.owner_branch_id)
        if self.run_state.last_branch_id is None:
            return self.run_state.context
        return self.run_state.context_for_branch(self.run_state.last_branch_id)

    def _create_activation(
        self,
        branch: Branch,
        *,
        input_value: Any,
    ) -> Activation:
        activation = Activation(
            id=f"activation-{uuid4()}",
            branch_id=branch.id,
            node_name=branch.current_node_name,
            node=resolve_node(
                self.run_state.workflow.name,
                self._resolve_current_node(branch.current_node_name),
            ),
            input_value=input_value,
            is_entry=branch.is_entry,
            treat_entry_dict_as_named_payload=(
                self.run_state.entry_treat_dict_as_named_payload
            ),
        )
        self.run_state.activations[activation.id] = activation
        self._open_join_scopes(activation, branch)
        return activation

    def _create_join_activation(
        self,
        *,
        join_name: str,
        join_instance: JoinInstance,
    ) -> JoinActivation:
        join = self.run_state.graph.nodes[join_name]
        if not isinstance(join, Join):
            raise RuntimeError(f"Node '{join_name}' is not a Join.")
        join_state = self.run_state.join_states[join_name]
        activation = JoinActivation(
            id=f"join-activation:{join_instance.id}",
            branch_id=join_instance.owner_branch_id,
            node_name=join_name,
            join=join,
            join_instance_id=join_instance.id,
            reducer=join_state.reducer,
            input_value=list(join_instance.contributions),
        )
        self.run_state.activations[activation.id] = activation
        return activation

    def _create_branch(
        self,
        *,
        current_node_name: str | None,
        is_entry: bool,
        parent_branch_id: str | None = None,
    ) -> Branch:
        parent = (
            None
            if parent_branch_id is None
            else self.run_state.branches[parent_branch_id]
        )
        branch = Branch(
            id=f"branch-{uuid4()}",
            current_node_name=current_node_name,
            _is_entry=is_entry,
            scope_instances={} if parent is None else dict(parent.scope_instances),
        )
        self.run_state.branches[branch.id] = branch
        if parent is None:
            self.run_state.initialize_branch_context(branch.id)
        else:
            self.run_state.inherit_branch_context(
                branch.id,
                parent_branch_id=parent.id,
            )
            for join_name, instance_id in branch.scope_instances.items():
                self.run_state.join_states[join_name].instances[
                    instance_id
                ].active_branch_ids.add(branch.id)
        return branch

    def _resolve_current_node(self, node_name: str | None) -> Any:
        if node_name == "start":
            return self.run_state.graph.start
        if node_name is None:
            raise RuntimeError("Cannot resolve current node without a node name.")
        return self.run_state.graph.nodes[node_name]
