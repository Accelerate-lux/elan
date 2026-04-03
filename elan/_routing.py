from typing import Any

from pydantic import BaseModel

from ._binding import _MappedPayload
from ._refs import ModelFieldRef
from .node import Node
from .task import Task
from .when import When


def is_string_target_list(next_value: Any) -> bool:
    return isinstance(next_value, list) and all(
        isinstance(target, str) for target in next_value
    )


def is_when_list(next_value: Any) -> bool:
    return isinstance(next_value, list) and all(
        isinstance(target, When) for target in next_value
    )


def resolve_next_targets(
    workflow_name: str,
    *,
    next_value: str | list[str] | list[When] | dict[str, str] | None,
    route_on: str | None,
    emitted_value: Any,
    nodes: dict[str, Task | str | Node],
) -> list[tuple[str, Task | str | Node]]:
    if next_value is None:
        return []

    if isinstance(next_value, str):
        return [_resolve_target(workflow_name, next_value, nodes)]

    if is_string_target_list(next_value):
        return [
            _resolve_target(workflow_name, target_name, nodes)
            for target_name in next_value
        ]

    if is_when_list(next_value):
        targets: list[tuple[str, Task | str | Node]] = []
        for when in next_value:
            if _resolve_when_condition(
                workflow_name,
                condition=when.condition,
                value=emitted_value,
            ):
                targets.extend(
                    _resolve_when_target(
                        workflow_name,
                        target=when.target,
                        nodes=nodes,
                    )
                )
        return targets

    if isinstance(next_value, list):
        raise TypeError(
            f"Workflow '{workflow_name}' cannot mix raw node ids and When(...) in the same next list."
        )

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
        "Only string, list, dict, and When(...) routing are implemented in the current runtime."
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


def _resolve_when_condition(
    workflow_name: str,
    *,
    condition: str | ModelFieldRef,
    value: Any,
) -> bool:
    if isinstance(condition, str):
        resolved = _resolve_string_condition(
            workflow_name,
            field_name=condition,
            value=value,
        )
    elif isinstance(condition, ModelFieldRef):
        resolved = _resolve_model_condition(
            workflow_name,
            ref=condition,
            value=value,
        )
    else:
        raise TypeError(
            f"Workflow '{workflow_name}' uses an unsupported When condition of type {type(condition).__name__}."
        )

    if not isinstance(resolved, bool):
        condition_name = (
            condition if isinstance(condition, str) else f"{condition.model.__name__}.{condition.field_name}"
        )
        raise TypeError(
            f"Workflow '{workflow_name}' requires When condition '{condition_name}' to resolve to bool."
        )

    return resolved


def _resolve_string_condition(
    workflow_name: str,
    *,
    field_name: str,
    value: Any,
) -> Any:
    if isinstance(value, _MappedPayload):
        if field_name not in value.values:
            raise TypeError(
                f"Workflow '{workflow_name}' condition source does not provide field '{field_name}'."
            )
        return value.values[field_name]

    if isinstance(value, dict):
        if field_name not in value:
            raise TypeError(
                f"Workflow '{workflow_name}' condition source does not provide field '{field_name}'."
            )
        return value[field_name]

    raise TypeError(
        f"Workflow '{workflow_name}' cannot read When condition '{field_name}' from value of type {type(value).__name__}."
    )


def _resolve_model_condition(
    workflow_name: str,
    *,
    ref: ModelFieldRef,
    value: Any,
) -> Any:
    if not isinstance(value, BaseModel):
        raise TypeError(
            f"Workflow '{workflow_name}' cannot read When condition '{ref.model.__name__}.{ref.field_name}' "
            f"from value of type {type(value).__name__}."
        )

    if not isinstance(value, ref.model):
        raise TypeError(
            f"Workflow '{workflow_name}' cannot read When condition '{ref.model.__name__}.{ref.field_name}' "
            f"from model value of type {type(value).__name__}."
        )

    if ref.field_name not in ref.model.model_fields:
        raise TypeError(
            f"Workflow '{workflow_name}' condition source does not provide field '{ref.field_name}'."
        )

    return getattr(value, ref.field_name)


def _resolve_when_target(
    workflow_name: str,
    *,
    target: str | list[str],
    nodes: dict[str, Task | str | Node],
) -> list[tuple[str, Task | str | Node]]:
    if isinstance(target, str):
        return [_resolve_target(workflow_name, target, nodes)]

    if isinstance(target, list) and all(isinstance(item, str) for item in target):
        return [_resolve_target(workflow_name, item, nodes) for item in target]

    raise TypeError(
        f"Workflow '{workflow_name}' uses an unsupported When target of type {type(target).__name__}."
    )
