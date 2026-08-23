from __future__ import annotations

from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4

from ._binding import _MappedPayload
from ._join_state import JoinState
from ._resolution import resolve_node, resolve_task_ref
from ._run_state import RunState
from .binding import Binder
from .expand import Expand, _BoundExpand
from .fragment import Fragment
from .join import Join
from .node import Node
from .task import Task
from .when import When


@dataclass(frozen=True, slots=True)
class MaterializedFragment:
    entry_name: str
    nodes: dict[str, Task | str | Node | Join | Any]
    join_states: dict[str, JoinState]


def materialize_expansion(
    run_state: RunState,
    site: Expand | _BoundExpand,
    emitted_value: Any,
) -> MaterializedFragment:
    if run_state.policy is None or not run_state.policy.allow_runtime_expansion:
        raise TypeError(
            f"Workflow '{run_state.workflow.name}' does not allow runtime expansion."
        )

    expand = site.expand if isinstance(site, _BoundExpand) else site
    builder_value = (
        dict(emitted_value.values)
        if isinstance(emitted_value, _MappedPayload)
        else emitted_value
    )
    validated_value = expand._input_adapter.validate_python(builder_value)
    fragment = expand.builder(validated_value)
    if not isinstance(fragment, Fragment):
        raise TypeError(
            f"Expand builder '{_builder_name(expand)}' returned "
            f"{type(fragment).__name__}; expected Fragment."
        )

    outer_scope = (
        dict(site.lexical_scope)
        if isinstance(site, _BoundExpand)
        else {
            name: name
            for name in run_state.graph.static_node_names
        }
    )
    return _materialize_fragment(run_state, fragment, outer_scope=outer_scope)


def graph_contains_expand(start: Any, nodes: Mapping[str, Any]) -> bool:
    return any(
        _next_contains_expand(value.next)
        for value in (start, *nodes.values())
        if isinstance(value, (Node, Join))
    )


def validate_expand_placement(
    workflow_name: str,
    start: Any,
    nodes: Mapping[str, Any],
) -> None:
    for node_name, value in (("start", start), *nodes.items()):
        if not isinstance(value, (Node, Join)):
            continue
        _validate_next_expansion_placement(
            workflow_name,
            node_name=node_name,
            next_value=value.next,
            top_level=True,
        )


def _materialize_fragment(
    run_state: RunState,
    fragment: Fragment,
    *,
    outer_scope: dict[str, str],
) -> MaterializedFragment:
    declarations = {"start": fragment.start, **dict(fragment.nodes)}
    prefix = _unique_prefix(run_state, declarations)
    local_ids = {name: f"{prefix}{name}" for name in declarations}
    visible_scope = {**outer_scope, **local_ids}

    join_scopes = _resolve_fragment_join_scopes(
        run_state.workflow.name,
        declarations,
        local_ids=local_ids,
    )
    materialized_nodes: dict[str, Any] = {}
    for local_name, declaration in declarations.items():
        materialized_name = local_ids[local_name]
        materialized_nodes[materialized_name] = _materialize_declaration(
            run_state.workflow.name,
            declaration,
            visible_scope=visible_scope,
            join_scope=join_scopes.get(local_name),
        )

    candidate_nodes = dict(run_state.graph.nodes)
    collision = set(candidate_nodes).intersection(materialized_nodes)
    if collision:
        names = ", ".join(sorted(collision))
        raise RuntimeError(
            f"Workflow '{run_state.workflow.name}' expansion namespace collided with: {names}."
        )
    candidate_nodes.update(materialized_nodes)

    _validate_candidate_graph(
        run_state,
        nodes=candidate_nodes,
    )
    join_states = _create_materialized_join_states(
        run_state.workflow.name,
        materialized_nodes,
    )
    return MaterializedFragment(
        entry_name=local_ids["start"],
        nodes=materialized_nodes,
        join_states=join_states,
    )


def _unique_prefix(run_state: RunState, declarations: Mapping[str, Any]) -> str:
    while True:
        prefix = f"__expand_{uuid4().hex}:"
        generated = {f"{prefix}{name}" for name in declarations}
        if not generated.intersection(run_state.graph.nodes):
            return prefix


def _resolve_fragment_join_scopes(
    workflow_name: str,
    declarations: Mapping[str, Any],
    *,
    local_ids: Mapping[str, str],
) -> dict[str, str]:
    resolved: dict[str, str] = {}
    joins_by_scope: dict[str, list[str]] = {}
    for join_name, declaration in declarations.items():
        if not isinstance(declaration, Join):
            continue
        if declaration.scope is None:
            raise TypeError(
                f"Workflow '{workflow_name}' Fragment Join '{join_name}' requires an explicit local scope."
            )
        if isinstance(declaration.scope, str):
            scope_name = declaration.scope
        else:
            matches = [
                name
                for name, value in declarations.items()
                if value is declaration.scope
            ]
            if not matches:
                raise TypeError(
                    f"Workflow '{workflow_name}' Fragment Join '{join_name}' scope must belong to the same Fragment."
                )
            scope_name = matches[0]

        if scope_name not in declarations:
            raise TypeError(
                f"Workflow '{workflow_name}' Fragment Join '{join_name}' references non-local scope '{scope_name}'."
            )
        if isinstance(declarations[scope_name], Join):
            raise TypeError(
                f"Workflow '{workflow_name}' Fragment Join '{join_name}' scope '{scope_name}' must be executable."
            )
        resolved[join_name] = local_ids[scope_name]
        joins_by_scope.setdefault(scope_name, []).append(join_name)

    for scope_name, join_names in joins_by_scope.items():
        if len(join_names) > 1:
            raise TypeError(
                f"Workflow '{workflow_name}' Fragment defines multiple joins for scope "
                f"'{scope_name}': {', '.join(join_names)}."
            )
    return resolved


def _materialize_declaration(
    workflow_name: str,
    declaration: Any,
    *,
    visible_scope: Mapping[str, str],
    join_scope: str | None,
) -> Any:
    if isinstance(declaration, Node):
        return replace(
            declaration,
            next=_rewrite_next(
                workflow_name,
                declaration.next,
                visible_scope=visible_scope,
            ),
        )
    if isinstance(declaration, Join):
        return replace(
            declaration,
            scope=join_scope,
            next=_rewrite_next(
                workflow_name,
                declaration.next,
                visible_scope=visible_scope,
            ),
        )
    return declaration


def _rewrite_next(
    workflow_name: str,
    value: Any,
    *,
    visible_scope: Mapping[str, str],
) -> Any:
    if value is None:
        return None
    if isinstance(value, (Expand, _BoundExpand)):
        expand = value.expand if isinstance(value, _BoundExpand) else value
        return _BoundExpand(
            expand=expand,
            lexical_scope=MappingProxyType(dict(visible_scope)),
        )
    if isinstance(value, str):
        return _resolve_lexical_target(workflow_name, value, visible_scope)
    if isinstance(value, When):
        return replace(
            value,
            target=_rewrite_when_target(
                workflow_name,
                value.target,
                visible_scope=visible_scope,
            ),
        )
    if isinstance(value, list):
        return [
            _rewrite_next(
                workflow_name,
                item,
                visible_scope=visible_scope,
            )
            for item in value
        ]
    if isinstance(value, dict):
        return {
            route: _rewrite_next(
                workflow_name,
                target,
                visible_scope=visible_scope,
            )
            for route, target in value.items()
        }
    raise TypeError(
        f"Workflow '{workflow_name}' Fragment uses unsupported next value "
        f"of type {type(value).__name__}."
    )


def _rewrite_when_target(
    workflow_name: str,
    value: Any,
    *,
    visible_scope: Mapping[str, str],
) -> Any:
    if isinstance(value, str):
        return _resolve_lexical_target(workflow_name, value, visible_scope)
    if isinstance(value, list):
        return [
            _resolve_lexical_target(workflow_name, item, visible_scope)
            if isinstance(item, str)
            else item
            for item in value
        ]
    return value


def _resolve_lexical_target(
    workflow_name: str,
    target_name: str,
    visible_scope: Mapping[str, str],
) -> str:
    if target_name not in visible_scope:
        raise KeyError(
            f"Workflow '{workflow_name}' Fragment references unknown lexical node '{target_name}'."
        )
    return visible_scope[target_name]


def _validate_candidate_graph(
    run_state: RunState,
    *,
    nodes: Mapping[str, Any],
) -> None:
    workflow_name = run_state.workflow.name
    graph = {"start": run_state.graph.start, **nodes}
    if isinstance(run_state.graph.start, Join):
        raise TypeError(
            f"Workflow '{workflow_name}' requires start to be executable, not Join(...)."
        )

    joins_by_scope: dict[str, list[str]] = {}
    for node_name, declaration in graph.items():
        if isinstance(declaration, Join):
            if node_name == "start":
                raise TypeError(
                    f"Workflow '{workflow_name}' requires start to be executable, not Join(...)."
                )
            if node_name == "result" and declaration.next is not None:
                raise TypeError(
                    f"Workflow '{workflow_name}' requires the reserved result node to be terminal."
                )
            if node_name != "result" and declaration.scope is None:
                raise TypeError(
                    f"Workflow '{workflow_name}' Join '{node_name}' requires an explicit scope."
                )
            if declaration.run is not None:
                resolve_task_ref(workflow_name, declaration.run)
            if declaration.scope is not None:
                scope_name = declaration.scope
                if not isinstance(scope_name, str) or scope_name not in graph:
                    raise TypeError(
                        f"Workflow '{workflow_name}' Join '{node_name}' references unknown scope '{scope_name}'."
                    )
                if isinstance(graph[scope_name], Join):
                    raise TypeError(
                        f"Workflow '{workflow_name}' Join scope '{scope_name}' must be executable."
                    )
                joins_by_scope.setdefault(scope_name, []).append(node_name)
        else:
            resolved = resolve_node(workflow_name, declaration)
            _validate_context_binding(
                workflow_name,
                node_name=node_name,
                node=resolved,
                context_cls=run_state.workflow.context_cls,
            )

        if isinstance(declaration, (Node, Join)):
            if node_name == "result" and declaration.next is not None:
                raise TypeError(
                    f"Workflow '{workflow_name}' requires the reserved result node to be terminal."
                )
            _validate_next(
                workflow_name,
                node_name=node_name,
                next_value=declaration.next,
                route_on=declaration.route_on,
                nodes=nodes,
            )

    for scope_name, join_names in joins_by_scope.items():
        if len(join_names) > 1:
            raise TypeError(
                f"Workflow '{workflow_name}' defines multiple joins for scope "
                f"'{scope_name}': {', '.join(join_names)}."
            )

    if (
        run_state.policy is not None
        and not run_state.policy.allow_cycles
        and has_static_cycle(run_state.graph.start, nodes)
    ):
        raise TypeError(
            f"Workflow '{workflow_name}' expansion creates a static cycle but policy does not allow cycles."
        )


def _validate_context_binding(
    workflow_name: str,
    *,
    node_name: str,
    node: Node,
    context_cls: type[Any] | None,
) -> None:
    mapping = node.context
    if not isinstance(mapping, Binder):
        return
    if mapping.target_kind == "task":
        raise TypeError(
            f"Workflow '{workflow_name}' cannot use Binder[{mapping.target_name}] "
            f"as context for node '{node_name}'; use Binder[ContextModel] instead."
        )
    if (
        mapping.model_cls is not None
        and context_cls is not None
        and mapping.model_cls is not context_cls
    ):
        raise TypeError(
            f"Workflow '{workflow_name}' cannot use Binder[{mapping.model_cls.__name__}] "
            f"as context for node '{node_name}' with workflow context '{context_cls.__name__}'."
        )


def _validate_next(
    workflow_name: str,
    *,
    node_name: str,
    next_value: Any,
    route_on: Any,
    nodes: Mapping[str, Any],
) -> None:
    _validate_next_expansion_placement(
        workflow_name,
        node_name=node_name,
        next_value=next_value,
        top_level=True,
    )
    if next_value is None or isinstance(next_value, (Expand, _BoundExpand)):
        return
    if isinstance(next_value, str):
        _validate_target(workflow_name, next_value, nodes)
        return
    if isinstance(next_value, list):
        for item in next_value:
            if isinstance(item, str):
                _validate_target(workflow_name, item, nodes)
            elif isinstance(item, When):
                targets = (
                    [item.target]
                    if isinstance(item.target, str)
                    else item.target
                )
                if not isinstance(targets, list) or not all(
                    isinstance(target, str) for target in targets
                ):
                    raise TypeError(
                        f"Workflow '{workflow_name}' node '{node_name}' uses an unsupported When target."
                    )
                for target in targets:
                    _validate_target(workflow_name, target, nodes)
            else:
                raise TypeError(
                    f"Workflow '{workflow_name}' node '{node_name}' uses an unsupported next list entry."
                )
        return
    if isinstance(next_value, dict):
        if route_on is None:
            raise TypeError(
                f"Workflow '{workflow_name}' node '{node_name}' requires route_on when next is a mapping."
            )
        if not all(isinstance(target, str) for target in next_value.values()):
            raise TypeError(
                f"Workflow '{workflow_name}' node '{node_name}' mapping routes must target node names."
            )
        for target in next_value.values():
            _validate_target(workflow_name, target, nodes)
        return
    raise TypeError(
        f"Workflow '{workflow_name}' node '{node_name}' uses unsupported next value "
        f"of type {type(next_value).__name__}."
    )


def _validate_target(
    workflow_name: str,
    target_name: str,
    nodes: Mapping[str, Any],
) -> None:
    if target_name not in nodes:
        raise KeyError(
            f"Workflow '{workflow_name}' references unknown node '{target_name}'."
        )


def _validate_next_expansion_placement(
    workflow_name: str,
    *,
    node_name: str,
    next_value: Any,
    top_level: bool,
) -> None:
    if isinstance(next_value, (Expand, _BoundExpand)):
        if not top_level:
            raise TypeError(
                f"Workflow '{workflow_name}' node '{node_name}' must use Expand as its complete next value."
            )
        return
    if isinstance(next_value, When):
        _validate_next_expansion_placement(
            workflow_name,
            node_name=node_name,
            next_value=next_value.target,
            top_level=False,
        )
        return
    if isinstance(next_value, list):
        for value in next_value:
            _validate_next_expansion_placement(
                workflow_name,
                node_name=node_name,
                next_value=value,
                top_level=False,
            )
        return
    if isinstance(next_value, dict):
        for value in next_value.values():
            _validate_next_expansion_placement(
                workflow_name,
                node_name=node_name,
                next_value=value,
                top_level=False,
            )


def _next_contains_expand(value: Any) -> bool:
    if isinstance(value, (Expand, _BoundExpand)):
        return True
    if isinstance(value, When):
        return _next_contains_expand(value.target)
    if isinstance(value, list):
        return any(_next_contains_expand(item) for item in value)
    if isinstance(value, dict):
        return any(_next_contains_expand(item) for item in value.values())
    return False


def has_static_cycle(start: Any, nodes: Mapping[str, Any]) -> bool:
    graph = {"start": start, **nodes}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_name: str) -> bool:
        if node_name in visiting:
            return True
        if node_name in visited:
            return False
        declaration = graph.get(node_name)
        if declaration is None:
            return False

        visiting.add(node_name)
        for target in _target_names(
            declaration.next if isinstance(declaration, (Node, Join)) else None
        ):
            if target in graph and visit(target):
                return True
        visiting.remove(node_name)
        visited.add(node_name)
        return False

    return any(visit(node_name) for node_name in graph)


def _target_names(value: Any) -> set[str]:
    if value is None or isinstance(value, (Expand, _BoundExpand)):
        return set()
    if isinstance(value, str):
        return {value}
    if isinstance(value, When):
        return _target_names(value.target)
    if isinstance(value, list):
        return (
            set().union(*(_target_names(item) for item in value))
            if value
            else set()
        )
    if isinstance(value, dict):
        return (
            set().union(*(_target_names(item) for item in value.values()))
            if value
            else set()
        )
    return set()


def _create_materialized_join_states(
    workflow_name: str,
    nodes: Mapping[str, Any],
) -> dict[str, JoinState]:
    states: dict[str, JoinState] = {}
    for node_name, declaration in nodes.items():
        if not isinstance(declaration, Join):
            continue
        reducer = (
            None
            if declaration.run is None
            else resolve_task_ref(workflow_name, declaration.run)
        )
        states[node_name] = JoinState(
            node_name=node_name,
            reducer=reducer,
            scope_node_name=declaration.scope,
        )
    return states


def _builder_name(expand: Expand) -> str:
    return getattr(expand.builder, "__name__", type(expand.builder).__name__)


__all__ = [
    "MaterializedFragment",
    "graph_contains_expand",
    "has_static_cycle",
    "materialize_expansion",
    "validate_expand_placement",
]
