import inspect
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, TypeAdapter, ValidationError

from .task import Task


@dataclass(frozen=True)
class _MappedPayload:
    values: dict[str, Any]


def bind_entry_input(
    target: Task, value: dict[str, Any]
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    return (), _bind_named_payload(target, value)


def bind_input(target: Task, value: Any) -> tuple[tuple[Any, ...], dict[str, Any]]:
    if isinstance(value, _MappedPayload):
        return (), _bind_named_payload(target, value.values)

    if isinstance(value, BaseModel):
        return _bind_model_payload(target, value)

    if isinstance(value, tuple):
        return _bind_tuple_payload(target, value)

    return _bind_scalar_payload(target, value)


def map_output(output_spec: str | list[Any] | None, output: Any) -> Any:
    if output_spec is None:
        return output

    names = [output_spec] if isinstance(output_spec, str) else output_spec
    values = output if isinstance(output, (tuple, list)) else (output,)
    mapped: dict[str, Any] = {}
    for index, name in enumerate(names):
        if index >= len(values):
            break
        if name in (None, Ellipsis):
            continue
        mapped[str(name)] = values[index]
    return _MappedPayload(mapped)


def _bind_named_payload(target: Task, value: dict[str, Any]) -> dict[str, Any]:
    bound: dict[str, Any] = {}
    missing: list[str] = []

    for parameter in target.parameters:
        if parameter.name in value:
            bound[parameter.name] = _validate_value(
                target,
                parameter.name,
                parameter.annotation,
                value[parameter.name],
            )
        elif parameter.default is inspect.Signature.empty:
            missing.append(parameter.name)

    if missing:
        raise TypeError(
            f"Task '{target.name}' is missing required inputs: {', '.join(missing)}."
        )

    return bound


def _bind_model_payload(
    target: Task, value: BaseModel
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    if _expects_model_instance(target, value):
        return (value,), {}

    return (), _bind_named_payload(target, value.model_dump())


def _expects_model_instance(target: Task, value: BaseModel) -> bool:
    if len(target.parameters) != 1:
        return False

    annotation = target.parameters[0].annotation
    if annotation is inspect.Signature.empty:
        return False

    try:
        return isinstance(value, annotation)
    except TypeError:
        return False


def _bind_tuple_payload(
    target: Task, value: tuple[Any, ...]
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    if len(value) != len(target.parameters):
        raise TypeError(
            f"Cannot bind tuple output of length {len(value)} to task '{target.name}' "
            f"with {len(target.parameters)} parameters."
        )

    bound = tuple(
        _validate_value(target, parameter.name, parameter.annotation, item)
        for parameter, item in zip(target.parameters, value, strict=True)
    )
    return bound, {}


def _bind_scalar_payload(
    target: Task, value: Any
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    if not target.parameters:
        return (), {}

    if len(target.parameters) != 1:
        raise TypeError(
            f"Cannot bind input of type {type(value).__name__} to "
            f"task '{target.name}' automatically."
        )

    parameter = target.parameters[0]
    return (
        (
            _validate_value(
                target,
                parameter.name,
                parameter.annotation,
                value,
            ),
        ),
        {},
    )


def _validate_value(
    target: Task,
    parameter_name: str,
    annotation: Any,
    value: Any,
) -> Any:
    if annotation is inspect.Signature.empty:
        return value

    try:
        return TypeAdapter(annotation).validate_python(value)
    except ValidationError as exc:
        raise TypeError(
            f"Input for parameter '{parameter_name}' of task '{target.name}' "
            f"is not compatible with annotation {annotation!r}."
        ) from exc
