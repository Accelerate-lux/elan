from typing import Any

from pydantic import BaseModel

from ._context import prepare_context
from ._graph_state import GraphState
from ._join_state import JoinState
from ._orchestrator import Orchestrator
from ._refs import RefLookup
from ._resolution import resolve_task_ref
from ._run_state import RunState
from .join import Join
from .node import Node
from .result import WorkflowRun
from .task import Task, task

_UNSET = object()


class Workflow:
    def __init__(
        self,
        name: str | object = _UNSET,
        start: Task | str | Node | object = _UNSET,
        context: type[BaseModel] | None | object = _UNSET,
        bind_context: dict[str, Any] | None | object = _UNSET,
        **nodes: Task | str | Node | Join,
    ) -> None:
        if type(self) is not Workflow:
            if (
                name is not _UNSET
                or start is not _UNSET
                or context is not _UNSET
                or bind_context is not _UNSET
                or nodes
            ):
                raise TypeError(
                    f"Workflow subclass '{type(self).__name__}' does not accept constructor arguments."
                )
            name, start, context, bind_context, nodes = self._class_declaration()
        else:
            if name is _UNSET or start is _UNSET:
                raise TypeError("Workflow constructor requires 'name' and 'start'.")
            if context is _UNSET:
                context = None
            if bind_context is _UNSET:
                bind_context = None

        self._initialize(
            name=name,
            start=start,
            context=context,
            bind_context=bind_context,
            nodes=nodes,
        )

    @classmethod
    def _class_declaration(
        cls,
    ) -> tuple[
        str,
        Task | str | Node,
        type[BaseModel] | None,
        dict[str, Any] | None,
        dict[str, Task | str | Node | Join],
    ]:
        declared_name: str | None = None
        declared_start: Task | str | Node | object = _UNSET
        declared_context: type[BaseModel] | None = None
        declared_bind_context: dict[str, Any] | None = None
        declared_nodes: dict[str, Task | str | Node | Join] = {}

        for declaration_cls in reversed(cls.mro()):
            if declaration_cls in (object, Workflow):
                continue
            for declaration_name, value in declaration_cls.__dict__.items():
                if declaration_name.startswith("_"):
                    continue
                if declaration_name == "name":
                    declared_name = value
                    continue
                if declaration_name == "start":
                    declared_start = value
                    continue
                if declaration_name == "context":
                    declared_context = value
                    continue
                if declaration_name == "bind_context":
                    declared_bind_context = value
                    continue
                if _is_node_declaration(value):
                    declared_nodes[declaration_name] = value

        if declared_start is _UNSET:
            raise TypeError(f"Workflow subclass '{cls.__name__}' must declare 'start'.")

        return (
            cls.__name__ if declared_name is None else declared_name,
            declared_start,
            declared_context,
            declared_bind_context,
            declared_nodes,
        )

    def _initialize(
        self,
        *,
        name: str,
        start: Task | str | Node,
        context: type[BaseModel] | None,
        bind_context: dict[str, Any] | None,
        nodes: dict[str, Task | str | Node | Join],
    ) -> None:
        if context is not None and (
            not isinstance(context, type) or not issubclass(context, BaseModel)
        ):
            raise TypeError("Workflow context must be a Pydantic model class or None.")
        if isinstance(start, Join):
            raise TypeError(
                f"Workflow '{name}' only allows Join(...) as the reserved result node."
            )
        for node_name, node_value in nodes.items():
            if isinstance(node_value, Join) and node_name != "result":
                raise TypeError(
                    f"Workflow '{name}' only allows Join(...) as the reserved result node."
                )

        self.name = name
        self.start = start
        self.context_cls = context
        self.bind_context = bind_context
        self.nodes = dict(nodes)

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
            context=self._create_context(workflow_input),
            join_state=self._create_join_state(),
        )

    def _create_context(self, workflow_input: dict[str, Any]) -> BaseModel | None:
        if self.context_cls is None:
            if self.bind_context is not None:
                raise TypeError(
                    f"Workflow '{self.name}' cannot use Workflow.bind_context without workflow context."
                )
            return None

        context = (
            self.context_cls()
            if self.bind_context is None
            else self.context_cls.model_construct()
        )
        lookup = RefLookup(
            workflow_input=workflow_input,
            context=context,
            upstream_value=None,
        )
        return prepare_context(
            workflow_name=self.name,
            branch_context=context,
            mapping=self.bind_context,
            lookup=lookup,
            phase_name="Workflow.bind_context",
        )

    def _create_join_state(self) -> JoinState | None:
        join_value = self.nodes.get("result")
        if not isinstance(join_value, Join):
            return None

        reducer = None
        if join_value.run is not None:
            reducer = resolve_task_ref(self.name, join_value.run)

        return JoinState(reducer=reducer)


def _is_node_declaration(value: Any) -> bool:
    return isinstance(value, (Task, str, Node, Join))


__all__ = ["Workflow", "task"]
