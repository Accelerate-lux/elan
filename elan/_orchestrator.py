from typing import Any
from uuid import uuid4

from ._activation import Activation
from ._binding import bind_output
from ._branch import Branch
from ._resolution import resolve_node
from ._routing import resolve_next_targets
from ._run_state import RunState
from ._scheduler import Scheduler
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
        scheduler = Scheduler()

        initial_branch = self._create_branch(
            current_node_name="start",
            is_entry=True,
        )
        initial_activation = self._create_activation(
            initial_branch,
            input_value=input,
        )
        scheduler.enqueue(initial_activation)
        self.run_state.status = "running"

        while True:
            settled = scheduler.next_settled(self.run_state)
            if settled is None:
                settled = await scheduler.update(self.run_state)
                if settled is None:
                    self.run_state.status = "completed"
                    return WorkflowRun(
                        result=self._final_result(),
                        outputs=self.run_state.outputs,
                    )

            self._record_output(settled)
            next_activations = self._progress_branch(settled)
            for next_activation in next_activations:
                scheduler.enqueue(next_activation)

    def _progress_branch(
        self,
        settled: Activation,
    ) -> list[Activation]:
        branch = self.run_state.branches[settled.branch_id]
        emitted_value = bind_output(settled.node.bind_output, settled.output)

        if isinstance(settled.node.next, (dict, list)):
            self.run_state.used_branching = True

        if isinstance(settled.node.next, list) and "result" in self.run_state.graph.nodes:
            raise NotImplementedError(
                "Fan-out with reserved result is not implemented before Join."
            )

        next_targets = resolve_next_targets(
            self.run_state.workflow.name,
            next_value=settled.node.next,
            route_on=settled.node.route_on,
            emitted_value=emitted_value,
            nodes=self.run_state.graph.nodes,
        )
        if not next_targets:
            return []

        if isinstance(settled.node.next, str):
            next_name, _next_node = next_targets[0]
            branch.advance_to(next_name)
            return [
                self._create_activation(
                    branch,
                    input_value=emitted_value,
                )
            ]

        if isinstance(settled.node.next, dict):
            next_name, _next_node = next_targets[0]
            branch.advance_to(next_name)
            return [
                self._create_activation(
                    branch,
                    input_value=emitted_value,
                )
            ]

        activations: list[Activation] = []
        for next_name, _next_node in next_targets:
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

    def _record_output(
        self,
        activation: Activation,
    ) -> None:
        self.run_state.last_output = activation.output
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

    def _resolve_current_node(self, node_name: str | None) -> Task | str | Node:
        if node_name == "start":
            return self.run_state.graph.start

        if node_name is None:
            raise RuntimeError("Cannot resolve current node without a node name.")

        return self.run_state.graph.nodes[node_name]
