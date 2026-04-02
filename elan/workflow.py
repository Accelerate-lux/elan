from typing import Any

from ._graph_state import GraphState
from ._orchestrator import Orchestrator
from ._run_state import RunState
from .node import Node
from .result import WorkflowRun
from .task import Task, task


class Workflow:
    def __init__(
        self,
        name: str,
        start: Task | str | Node,
        **nodes: Task | str | Node,
    ) -> None:
        self.name = name
        self.start = start
        self.nodes = nodes

    async def run(self, **input: Any) -> WorkflowRun:
        run_state = self._create_run_state()
        orchestrator = Orchestrator(run_state=run_state)
        return await orchestrator.run(**input)

    def _create_run_state(self) -> RunState:
        return RunState(
            workflow=self,
            graph=GraphState(
                start=self.start,
                nodes=dict(self.nodes),
            ),
        )


__all__ = ["Workflow", "task"]
