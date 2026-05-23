from __future__ import annotations

from dataclasses import replace
from typing import Any

from pydantic import BaseModel

from ._context import copy_context, prepare_context
from ._graph_state import GraphState
from ._join_state import JoinState
from ._orchestrator import Orchestrator
from ._policy import prepare_policy
from ._refs import RefLookup
from ._resolution import resolve_task_ref
from .binding import Binder
from ._run_state import RunState
from .join import Join
from .node import Node
from .policy import WorkflowPolicy
from .result import WorkflowRun
from .task import Task, task
from .when import When

_UNSET = object()


class _ForwardNodeRef:
    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return self.name


class _WorkflowClassNamespace(dict[str, Any]):
    def __getitem__(self, key: str) -> Any:
        try:
            return super().__getitem__(key)
        except KeyError:
            if self._is_forward_declared_node(key):
                ref = _ForwardNodeRef(key)
                self[key] = ref
                return ref
            raise

    def _is_forward_declared_node(self, key: str) -> bool:
        annotations = super().get("__annotations__", {})
        return key in annotations and _is_node_annotation(annotations[key])


class _WorkflowMeta(type):
    @classmethod
    def __prepare__(
        mcls,
        name: str,
        bases: tuple[type, ...],
        **kwargs: Any,
    ) -> _WorkflowClassNamespace:
        return _WorkflowClassNamespace()


class Workflow(metaclass=_WorkflowMeta):
    def __init__(
        self,
        name: str | object = _UNSET,
        start: Task | str | Node | "Workflow" | object = _UNSET,
        context: type[BaseModel] | None | object = _UNSET,
        bind_context: dict[str, Any] | Binder[Any] | None | object = _UNSET,
        policy: WorkflowPolicy | None | object = _UNSET,
        **nodes: Task | str | Node | Join | "Workflow",
    ) -> None:
        if type(self) is not Workflow:
            if (
                name is not _UNSET
                or start is not _UNSET
                or context is not _UNSET
                or bind_context is not _UNSET
                or policy is not _UNSET
                or nodes
            ):
                raise TypeError(
                    f"Workflow subclass '{type(self).__name__}' does not accept constructor arguments."
                )
            name, start, context, bind_context, policy, nodes = self._class_declaration()
        else:
            if name is _UNSET or start is _UNSET:
                raise TypeError("Workflow constructor requires 'name' and 'start'.")
            if context is _UNSET:
                context = None
            if bind_context is _UNSET:
                bind_context = None
            if policy is _UNSET:
                policy = None

        self._initialize(
            name=name,
            start=start,
            context=context,
            bind_context=bind_context,
            policy=policy,
            nodes=nodes,
        )

    @classmethod
    def _class_declaration(
        cls,
    ) -> tuple[
        str,
        Task | str | Node | "Workflow",
        type[BaseModel] | None,
        dict[str, Any] | Binder[Any] | None,
        WorkflowPolicy | None,
        dict[str, Task | str | Node | Join | "Workflow"],
    ]:
        declared_name: str | None = None
        declared_start: Task | str | Node | Workflow | object = _UNSET
        declared_context: type[BaseModel] | None = None
        declared_bind_context: dict[str, Any] | Binder[Any] | None = None
        declared_policy: WorkflowPolicy | None = None
        declared_nodes: dict[str, Task | str | Node | Join | Workflow] = {}
        forward_declarations: set[str] = set()

        for declaration_cls in reversed(cls.mro()):
            if declaration_cls in (object, Workflow):
                continue
            forward_declarations.update(_node_annotations(declaration_cls))
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
                if declaration_name == "policy":
                    declared_policy = value
                    continue
                if _is_node_declaration(value):
                    declared_nodes[declaration_name] = value

        if declared_start is _UNSET:
            raise TypeError(f"Workflow subclass '{cls.__name__}' must declare 'start'.")

        missing_forward_declarations = sorted(
            name for name in forward_declarations if name not in declared_nodes
        )
        if missing_forward_declarations:
            raise TypeError(
                f"Workflow subclass '{cls.__name__}' forward declares nodes that are not assigned: "
                f"{', '.join(missing_forward_declarations)}."
            )

        declared_start = _resolve_forward_refs(
            cls.__name__,
            declared_start,
            declared_nodes=declared_nodes,
        )
        declared_nodes = {
            node_name: _resolve_forward_refs(
                cls.__name__,
                node_value,
                declared_nodes=declared_nodes,
            )
            for node_name, node_value in declared_nodes.items()
        }

        return (
            cls.__name__ if declared_name is None else declared_name,
            declared_start,
            declared_context,
            declared_bind_context,
            declared_policy,
            declared_nodes,
        )

    def _initialize(
        self,
        *,
        name: str,
        start: Task | str | Node | "Workflow",
        context: type[BaseModel] | None,
        bind_context: dict[str, Any] | Binder[Any] | None,
        policy: WorkflowPolicy | None,
        nodes: dict[str, Task | str | Node | Join | "Workflow"],
    ) -> None:
        if context is not None and (
            not isinstance(context, type) or not issubclass(context, BaseModel)
        ):
            raise TypeError("Workflow context must be a Pydantic model class or None.")
        if policy is not None and not isinstance(policy, WorkflowPolicy):
            raise TypeError("Workflow policy must be a WorkflowPolicy instance or None.")
        if isinstance(start, Join):
            raise TypeError(
                f"Workflow '{name}' only allows Join(...) as the reserved result node."
            )
        if isinstance(bind_context, Binder) and (
            bind_context.target_kind == "task"
        ):
            raise TypeError(
                f"Workflow '{name}' cannot use Binder[{bind_context.target_name}] "
                "for Workflow.bind_context; use Binder[ContextModel] instead."
            )
        if isinstance(bind_context, Binder) and (
            bind_context.model_cls is not None
            and context is not None
            and bind_context.model_cls is not context
        ):
            raise TypeError(
                f"Workflow '{name}' cannot use Binder[{bind_context.model_cls.__name__}] "
                f"with workflow context '{context.__name__}'."
            )
        for node_name, node_value in {"start": start, **nodes}.items():
            if (
                isinstance(node_value, Node)
                and isinstance(node_value.context, Binder)
                and node_value.context.target_kind == "task"
            ):
                raise TypeError(
                    f"Workflow '{name}' cannot use Binder[{node_value.context.target_name}] "
                    f"as context for node '{node_name}'; use Binder[ContextModel] instead."
                )
            if (
                isinstance(node_value, Node)
                and isinstance(node_value.context, Binder)
                and node_value.context.model_cls is not None
                and context is not None
                and node_value.context.model_cls is not context
            ):
                raise TypeError(
                    f"Workflow '{name}' cannot use Binder[{node_value.context.model_cls.__name__}] "
                    f"as context for node '{node_name}' with workflow context '{context.__name__}'."
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
        self.policy = policy
        self.nodes = dict(nodes)

    async def run(self, **input: Any) -> WorkflowRun:
        return await self._run(**input)

    async def _run(self, **input: Any) -> WorkflowRun:
        run_state = self._create_run_state(
            input,
            workflow_input=dict(input),
            inherited_context=None,
            inherited_policy=None,
            input_is_workflow_input=True,
        )
        orchestrator = Orchestrator(run_state=run_state)
        return await orchestrator.run(input)

    async def _run_child(
        self,
        input_value: Any,
        *,
        inherited_context: BaseModel | None,
        inherited_policy: WorkflowPolicy | None,
        input_is_workflow_input: bool,
    ) -> WorkflowRun:
        workflow_input = (
            dict(input_value)
            if input_is_workflow_input and isinstance(input_value, dict)
            else _workflow_input_from_value(input_value)
        )
        run_state = self._create_run_state(
            input_value,
            workflow_input=workflow_input,
            inherited_context=inherited_context,
            inherited_policy=inherited_policy,
            input_is_workflow_input=input_is_workflow_input,
        )
        orchestrator = Orchestrator(run_state=run_state)
        return await orchestrator.run(input_value)

    def _create_run_state(
        self,
        input_value: Any,
        *,
        workflow_input: dict[str, Any] | None = None,
        inherited_context: BaseModel | None = None,
        inherited_policy: WorkflowPolicy | None = None,
        input_is_workflow_input: bool = True,
    ) -> RunState:
        if workflow_input is None:
            workflow_input = (
                dict(input_value)
                if isinstance(input_value, dict)
                else _workflow_input_from_value(input_value)
            )
        policy = self._create_policy(
            inherited_policy=inherited_policy,
        )
        self._validate_policy_allows_graph(policy)
        return RunState(
            workflow=self,
            graph=GraphState(
                start=self.start,
                nodes=dict(self.nodes),
            ),
            workflow_input=dict(workflow_input),
            policy=policy,
            context=self._create_context(
                workflow_input,
                inherited_context=inherited_context,
                policy=policy,
            ),
            join_state=self._create_join_state(),
            entry_treat_dict_as_named_payload=input_is_workflow_input,
        )

    def _create_context(
        self,
        workflow_input: dict[str, Any],
        *,
        inherited_context: BaseModel | None,
        policy: WorkflowPolicy | None,
    ) -> BaseModel | None:
        if inherited_context is not None:
            if (
                self.context_cls is not None
                and type(inherited_context) is not self.context_cls
            ):
                raise TypeError(
                    f"Workflow '{self.name}' cannot inherit context "
                    f"'{type(inherited_context).__name__}' as '{self.context_cls.__name__}'."
                )
            context = copy_context(inherited_context)
            if self.bind_context is None:
                return context
            lookup = RefLookup(
                workflow_input=workflow_input,
                context=context,
                policy=policy,
                upstream_value=None,
            )
            return prepare_context(
                workflow_name=self.name,
                branch_context=context,
                mapping=self.bind_context,
                lookup=lookup,
                phase_name="Workflow.bind_context",
            )

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
            policy=policy,
            upstream_value=None,
        )
        return prepare_context(
            workflow_name=self.name,
            branch_context=context,
            mapping=self.bind_context,
            lookup=lookup,
            phase_name="Workflow.bind_context",
        )

    def _create_policy(
        self,
        *,
        inherited_policy: WorkflowPolicy | None,
    ) -> WorkflowPolicy:
        return prepare_policy(
            workflow_name=self.name,
            declared_policy=self.policy,
            inherited_policy=inherited_policy,
        )

    def _create_join_state(self) -> JoinState | None:
        join_value = self.nodes.get("result")
        if not isinstance(join_value, Join):
            return None

        reducer = None
        if join_value.run is not None:
            reducer = resolve_task_ref(self.name, join_value.run)

        return JoinState(reducer=reducer)

    def _validate_policy_allows_graph(self, policy: WorkflowPolicy) -> None:
        if not policy.allow_cycles and _has_static_cycle(self.start, self.nodes):
            raise TypeError(
                f"Workflow '{self.name}' defines a static cycle but policy does not allow cycles."
            )


def _is_node_declaration(value: Any) -> bool:
    return isinstance(value, (Task, str, Node, Join, Workflow))


def _is_node_annotation(annotation: Any) -> bool:
    if annotation in (Node, Join):
        return True
    if isinstance(annotation, str):
        return annotation in {"Node", "Join"}
    return False


def _node_annotations(cls: type) -> set[str]:
    annotations = cls.__dict__.get("__annotations__", {})
    return {
        name
        for name, annotation in annotations.items()
        if not name.startswith("_")
        and name
        not in {
            "name",
            "context",
            "bind_context",
            "policy",
            "start",
        }
        and _is_node_annotation(annotation)
    }


def _resolve_forward_refs(
    workflow_class_name: str,
    value: Any,
    *,
    declared_nodes: dict[str, Task | str | Node | Join | Workflow],
) -> Any:
    if isinstance(value, _ForwardNodeRef):
        return _resolve_forward_ref(
            workflow_class_name,
            value,
            declared_nodes=declared_nodes,
        )

    if isinstance(value, Node):
        return replace(
            value,
            next=_resolve_next_forward_refs(
                workflow_class_name,
                value.next,
                declared_nodes=declared_nodes,
            ),
        )

    return value


def _resolve_next_forward_refs(
    workflow_class_name: str,
    next_value: Any,
    *,
    declared_nodes: dict[str, Task | str | Node | Join | Workflow],
) -> Any:
    if isinstance(next_value, _ForwardNodeRef):
        return _resolve_forward_ref(
            workflow_class_name,
            next_value,
            declared_nodes=declared_nodes,
        )

    if isinstance(next_value, list):
        return [
            _resolve_when_forward_refs(
                workflow_class_name,
                item,
                declared_nodes=declared_nodes,
            )
            if isinstance(item, When)
            else _resolve_next_forward_refs(
                workflow_class_name,
                item,
                declared_nodes=declared_nodes,
            )
            for item in next_value
        ]

    if isinstance(next_value, dict):
        return {
            key: _resolve_next_forward_refs(
                workflow_class_name,
                target,
                declared_nodes=declared_nodes,
            )
            for key, target in next_value.items()
        }

    return next_value


def _resolve_when_forward_refs(
    workflow_class_name: str,
    when: When,
    *,
    declared_nodes: dict[str, Task | str | Node | Join | Workflow],
) -> When:
    return replace(
        when,
        target=_resolve_next_forward_refs(
            workflow_class_name,
            when.target,
            declared_nodes=declared_nodes,
        ),
    )


def _resolve_forward_ref(
    workflow_class_name: str,
    ref: _ForwardNodeRef,
    *,
    declared_nodes: dict[str, Task | str | Node | Join | Workflow],
) -> str:
    if ref.name not in declared_nodes:
        raise TypeError(
            f"Workflow subclass '{workflow_class_name}' references forward-declared node "
            f"'{ref.name}' before assigning it."
        )
    return ref.name


def _has_static_cycle(
    start: Task | str | Node | Workflow,
    nodes: dict[str, Task | str | Node | Join | Workflow],
) -> bool:
    graph = {"start": start, **nodes}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_name: str) -> bool:
        if node_name in visiting:
            return True
        if node_name in visited:
            return False

        node_value = graph.get(node_name)
        if node_value is None:
            return False

        visiting.add(node_name)
        for next_name in _next_node_names(node_value):
            if next_name in graph and visit(next_name):
                return True
        visiting.remove(node_name)
        visited.add(node_name)
        return False

    return any(visit(node_name) for node_name in graph)


def _next_node_names(value: Any) -> set[str]:
    if not isinstance(value, Node):
        return set()
    return _target_node_names(value.next)


def _target_node_names(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {value}
    if isinstance(value, When):
        return _target_node_names(value.target)
    if isinstance(value, list):
        names: set[str] = set()
        for item in value:
            names.update(_target_node_names(item))
        return names
    if isinstance(value, dict):
        names: set[str] = set()
        for item in value.values():
            names.update(_target_node_names(item))
        return names
    return set()


def _workflow_input_from_value(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, BaseModel):
        return value.model_dump()
    return {}


__all__ = ["Workflow", "task"]
