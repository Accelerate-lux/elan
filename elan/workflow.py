from typing import Any

from pydantic import BaseModel

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
        context: type[BaseModel] | None = None,
        **nodes: Task | str | Node,
    ) -> None:
        if context is not None and (
            not isinstance(context, type) or not issubclass(context, BaseModel)
        ):
            raise TypeError(
                "Workflow context must be a Pydantic model class or None."
            )

        self.name = name
        self.start = start
        self.context_model = context
        self.nodes = nodes

    async def run(self, **input: Any) -> WorkflowRun:
        run_state = self._create_run_state(input)
        orchestrator = Orchestrator(run_state=run_state)
        return await orchestrator.run(**input)

    def _create_run_state(self, workflow_input: dict[str, Any]) -> RunState:
        return RunState(
            workflow=self,
            graph=GraphState(
                start=self.start,
                nodes=dict(self.nodes),
            ),
            workflow_input=dict(workflow_input),
            context_value=self._create_context_value(),
        )

    def _create_context_value(self) -> BaseModel | None:
        if self.context_model is None:
            return None

        return self.context_model()


__all__ = ["Workflow", "task"]
