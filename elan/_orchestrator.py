from typing import Any

from ._activation import Activation
from ._binding import map_output
from ._branch import Branch
from ._resolution import resolve_node
from ._routing import resolve_linear_next
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
            next_activation = self._progress_branch(settled)
            if next_activation is not None:
                scheduler.enqueue(next_activation)

    def _progress_branch(
        self,
        settled: Activation,
    ) -> Activation | None:
        branch = self.run_state.branches[settled.branch_id]
        next_target = resolve_linear_next(
            self.run_state.workflow.name,
            settled.node.next,
            self.run_state.graph.nodes,
        )
        if next_target is None:
            return None

        next_name, _next_node = next_target
        next_input = map_output(settled.node.output, settled.output)
        branch.advance_to(next_name)
        return self._create_activation(
            branch,
            input_value=next_input,
        )

    def _record_output(
        self,
        activation: Activation,
    ) -> None:
        self.run_state.last_output = activation.output
        self.run_state.outputs.setdefault(activation.node.run.name, []).append(
            activation.output
        )
        if activation.node_name == "result":
            self.run_state.result = activation.output

    def _final_result(self) -> Any:
        if self.run_state.result is not None:
            return self.run_state.result
        return self.run_state.last_output

    def _create_activation(
        self,
        branch: Branch,
        *,
        input_value: Any,
    ) -> Activation:
        self.run_state._activation_counter += 1
        activation = Activation(
            id=f"activation-{self.run_state._activation_counter}",
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
        self.run_state._branch_counter += 1
        branch = Branch(
            id=f"branch-{self.run_state._branch_counter}",
            _current_node_name=current_node_name,
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
