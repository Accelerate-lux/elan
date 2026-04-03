from typing import Any

from ._binding import _MappedPayload
from .node import Node
from .task import Task


def resolve_next_targets(
    workflow_name: str,
    *,
    next_value: str | list[str] | dict[str, str] | None,
    route_on: str | None,
    emitted_value: Any,
    nodes: dict[str, Task | str | Node],
) -> list[tuple[str, Task | str | Node]]:
    if next_value is None:
        return []

    if isinstance(next_value, str):
        return [_resolve_target(workflow_name, next_value, nodes)]

    if isinstance(next_value, list):
        return [
            _resolve_target(workflow_name, target_name, nodes)
            for target_name in next_value
        ]

    if isinstance(next_value, dict):
        if route_on is None:
            raise TypeError(
                f"Workflow '{workflow_name}' requires route_on when next is a mapping."
            )

        route_value = _resolve_route_value(
            workflow_name,
            field_name=route_on,
            value=emitted_value,
        )
        if route_value not in next_value:
            raise KeyError(
                f"Workflow '{workflow_name}' does not define a route for value {route_value!r}."
            )

        return [_resolve_target(workflow_name, next_value[route_value], nodes)]

    raise NotImplementedError(
        "Only string, list, and dict routing are implemented in the current runtime."
    )


def _resolve_target(
    workflow_name: str,
    target_name: str,
    nodes: dict[str, Task | str | Node],
) -> tuple[str, Task | str | Node]:
    if not isinstance(target_name, str):
        raise NotImplementedError(
            "Only string node ids are supported in the current routing runtime."
        )

    if target_name not in nodes:
        raise KeyError(
            f"Workflow '{workflow_name}' references unknown node '{target_name}'."
        )

    return target_name, nodes[target_name]


def _resolve_route_value(
    workflow_name: str,
    *,
    field_name: str,
    value: Any,
) -> Any:
    if isinstance(value, _MappedPayload):
        if field_name not in value.values:
            raise TypeError(
                f"Workflow '{workflow_name}' route source does not provide field '{field_name}'."
            )
        return value.values[field_name]

    if isinstance(value, dict):
        if field_name not in value:
            raise TypeError(
                f"Workflow '{workflow_name}' route source does not provide field '{field_name}'."
            )
        return value[field_name]

    raise TypeError(
        f"Workflow '{workflow_name}' cannot use route_on='{field_name}' with value of type {type(value).__name__}."
    )
