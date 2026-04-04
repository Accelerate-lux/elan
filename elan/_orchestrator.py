import asyncio
from typing import Any
from uuid import uuid4

from ._activation import Activation
from ._binding import bind_output
from ._branch import Branch
from ._resolution import resolve_node
from ._routing import (
    ResolvedNext,
    is_target_producer_list,
    resolve_next_targets,
)
from ._run_state import RunState
from ._scheduler import Scheduler
from .join import Join
from .node import Node
from .result import WorkflowRun
from .task import Task


class Orchestrator:
    def __init__(
        self,
        *,
        run_state: RunState,
    ) -> None:
        self.run_state = run_state

    async def run(self, **input: Any) -> WorkflowRun:
        scheduler = Scheduler(orchestrator=self)
        self._seed_run(scheduler, input)

        while True:
            settled = await self._next_settled_activation(scheduler)
            if settled is None:
                return await self._complete_run_or_raise(scheduler)

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
        initial_activation = self._create_activation(
            initial_branch,
            input_value=input_value,
        )
        scheduler.enqueue(initial_activation)
        self.run_state.mark_running()

    async def _next_settled_activation(
        self,
        scheduler: Scheduler,
    ) -> Activation | None:
        settled = scheduler.next_settled()
        if settled is not None:
            return settled

        return await scheduler.update()

    async def _complete_run_or_raise(
        self,
        scheduler: Scheduler,
    ) -> WorkflowRun:
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

        await self._finalize_join()
        self.run_state.mark_completed()
        return WorkflowRun(
            result=self._final_result(),
            outputs=self.run_state.outputs,
        )

    def activation_for_id(
        self,
        activation_id: str,
    ) -> Activation:
        return self.run_state.activations[activation_id]

    def _enqueue_next_activations(
        self,
        scheduler: Scheduler,
        settled: Activation,
    ) -> None:
        next_activations = self._progress_branch(settled)
        for next_activation in next_activations:
            scheduler.enqueue(next_activation)

    def _progress_branch(
        self,
        settled: Activation,
    ) -> list[Activation]:
        branch = self.run_state.branches[settled.branch_id]
        emitted_value = bind_output(settled.node.bind_output, settled.output)

        if isinstance(settled.node.next, dict) or is_target_producer_list(
            settled.node.next
        ):
            self.run_state.mark_branching_used()

        if (
            is_target_producer_list(settled.node.next)
            and "result" in self.run_state.graph.nodes
            and not self._uses_join_result()
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

    def _record_output(
        self,
        activation: Activation,
    ) -> None:
        self.run_state.last_output = activation.output
        branch_outputs = self.run_state.outputs.setdefault(activation.branch_id, {})
        branch_outputs.setdefault(activation.node.run.name, []).append(
            activation.output
        )
        if activation.node_name == "result":
            self.run_state.result = activation.output

    def _final_result(self) -> Any:
        if self.run_state.result is not None:
            return self.run_state.result
        if self.run_state.used_branching:
            return None
        return self.run_state.last_output

    async def _finalize_join(self) -> None:
        join_state = self.run_state.join_state
        if join_state is None or join_state.finalized:
            return

        contributions = list(join_state.contributions)
        if join_state.reducer is None:
            self.run_state.result = contributions
        else:
            self.run_state.result = await self._run_join_reducer(
                join_state.reducer,
                contributions,
            )
        join_state.finalized = True

    def _create_next_activations(
        self,
        branch: Branch,
        emitted_value: Any,
        next_targets: ResolvedNext,
    ) -> list[Activation]:
        if next_targets is None:
            branch.complete()
            return []

        if not isinstance(next_targets, list):
            next_name, _next_node = next_targets
            if self._uses_join_result() and next_name == "result":
                self._register_join_contribution(emitted_value)
                branch.complete()
                return []
            branch.advance_to(next_name)
            return [
                self._create_activation(
                    branch,
                    input_value=emitted_value,
                )
            ]

        branch.complete()
        activations: list[Activation] = []
        for next_name, _next_node in next_targets:
            if self._uses_join_result() and next_name == "result":
                self._register_join_contribution(emitted_value)
                continue
            child_branch = self._create_branch(
                current_node_name=next_name,
                is_entry=False,
            )
            activations.append(
                self._create_activation(
                    child_branch,
                    input_value=emitted_value,
                )
            )
        return activations

    def _register_join_contribution(
        self,
        emitted_value: Any,
    ) -> None:
        join_state = self.run_state.join_state
        if join_state is None:
            raise RuntimeError("Cannot register join contribution without join state.")

        join_state.contributions.append(emitted_value)

    def _uses_join_result(self) -> bool:
        return self.run_state.join_state is not None

    def _has_active_branches(self) -> bool:
        return any(
            not branch.is_complete for branch in self.run_state.branches.values()
        )

    async def _run_join_reducer(
        self,
        reducer: Task,
        contributions: list[Any],
    ) -> Any:
        if reducer.is_async:
            return await reducer.fn(contributions)
        return await asyncio.to_thread(reducer.fn, contributions)

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
        )
        self.run_state.activations[activation.id] = activation
        return activation

    def _create_branch(
        self,
        *,
        current_node_name: str | None,
        is_entry: bool,
    ) -> Branch:
        branch = Branch(
            id=f"branch-{uuid4()}",
            current_node_name=current_node_name,
            _is_entry=is_entry,
        )
        self.run_state.branches[branch.id] = branch
        return branch

    def _resolve_current_node(self, node_name: str | None) -> Task | str | Node | Join:
        if node_name == "start":
            return self.run_state.graph.start

        if node_name is None:
            raise RuntimeError("Cannot resolve current node without a node name.")

        return self.run_state.graph.nodes[node_name]
