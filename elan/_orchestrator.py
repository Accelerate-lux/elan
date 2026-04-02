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
            current=self.run_state.graph.start,
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
                    return WorkflowRun(result=self.run_state.result)

            self._record_output(settled.node.run.name, settled.output)
            next_activation = self._progress_branch(settled)
            if next_activation is not None:
                scheduler.enqueue(next_activation)

    def _progress_branch(
        self,
        settled: Activation,
    ) -> Activation | None:
        branch = self.run_state.branches[settled.branch_id]
        next_node = resolve_linear_next(
            self.run_state.workflow.name,
            settled.node.next,
            self.run_state.graph.nodes,
        )
        if next_node is None:
            return None

        next_input = map_output(settled.node.output, settled.output)
        branch.advance_to(next_node)
        return self._create_activation(
            branch,
            input_value=next_input,
        )

    def _record_output(
        self,
        task_name: str,
        output: Any,
    ) -> None:
        self.run_state.result.setdefault(task_name, []).append(output)

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
            node=resolve_node(self.run_state.workflow.name, branch.current),
            input_value=input_value,
            is_entry=branch.is_entry,
        )
        self.run_state.activations[activation.id] = activation
        return activation

    def _create_branch(
        self,
        *,
        current: Task | str | Node,
        is_entry: bool,
    ) -> Branch:
        self.run_state._branch_counter += 1
        branch = Branch(
            id=f"branch-{self.run_state._branch_counter}",
            current=current,
            _is_entry=is_entry,
        )
        self.run_state.branches[branch.id] = branch
        return branch
