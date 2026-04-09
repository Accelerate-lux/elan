import inspect
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, TypeAdapter, ValidationError

from ._refs import ModelFieldRef, RefLookup, SourceFieldRef
from .task import Task


@dataclass(frozen=True)
class _MappedPayload:
    values: dict[str, Any]


def bind_entry_input(
    target: Task,
    value: dict[str, Any],
    *,
    input_spec: dict[str, Any] | None = None,
    lookup: RefLookup | None = None,
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    if input_spec is not None:
        return (), _bind_with_input_spec(
            target,
            input_spec=input_spec,
            fallback_value=value,
            lookup=lookup or RefLookup(
                workflow_input=value,
                context=None,
                upstream_value=None,
            ),
            treat_dict_as_named_payload=True,
        )
    return (), _bind_named_payload(target, value)


def bind_input(
    target: Task,
    value: Any,
    *,
    input_spec: dict[str, Any] | None = None,
    lookup: RefLookup | None = None,
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    if input_spec is not None:
        return (), _bind_with_input_spec(
            target,
            input_spec=input_spec,
            fallback_value=value,
            lookup=lookup or RefLookup(
                workflow_input={},
                context=None,
                upstream_value=value,
            ),
            treat_dict_as_named_payload=False,
        )

    if isinstance(value, _MappedPayload):
        return (), _bind_named_payload(target, value.values)

    if isinstance(value, BaseModel):
        return _bind_model_payload(target, value)

    if isinstance(value, tuple):
        return _bind_tuple_payload(target, value)

    return _bind_scalar_payload(target, value)


def bind_output(output_spec: str | list[Any] | None, output: Any) -> Any:
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


def _bind_with_input_spec(
    target: Task,
    *,
    input_spec: dict[str, Any],
    fallback_value: Any,
    lookup: RefLookup,
    treat_dict_as_named_payload: bool,
) -> dict[str, Any]:
    parameter_names = {parameter.name for parameter in target.parameters}
    unknown = [name for name in input_spec if name not in parameter_names]
    if unknown:
        raise TypeError(
            f"Task '{target.name}' does not define parameters: {', '.join(unknown)}."
        )

    explicit = {
        parameter_name: _resolve_input_value(
            target,
            parameter_name=parameter_name,
            value=value,
            lookup=lookup,
        )
        for parameter_name, value in input_spec.items()
    }

    remaining_parameters = tuple(
        parameter
        for parameter in target.parameters
        if parameter.name not in explicit
    )
    automatic = _bind_remaining_parameters(
        target,
        parameters=remaining_parameters,
        value=fallback_value,
        treat_dict_as_named_payload=treat_dict_as_named_payload,
    )
    return {**automatic, **explicit}


def _resolve_input_value(
    target: Task,
    *,
    parameter_name: str,
    value: Any,
    lookup: RefLookup,
) -> Any:
    if isinstance(value, SourceFieldRef):
        resolved = value.eval(lookup, owner=f"task '{target.name}'")
    elif isinstance(value, ModelFieldRef):
        raise TypeError(
            f"Model field reference '{value.model.__name__}.{value.field_name}' "
            f"cannot be used as a binding source without Upstream/Input/Context."
        )
    else:
        resolved = value

    parameter = _parameter_by_name(target, parameter_name)
    return _validate_value(target, parameter.name, parameter.annotation, resolved)


def _bind_remaining_parameters(
    target: Task,
    *,
    parameters: tuple[inspect.Parameter, ...],
    value: Any,
    treat_dict_as_named_payload: bool,
) -> dict[str, Any]:
    if not parameters:
        return {}

    if isinstance(value, _MappedPayload):
        return _bind_named_payload_for_parameters(target, parameters, value.values)

    if treat_dict_as_named_payload and isinstance(value, dict):
        return _bind_named_payload_for_parameters(target, parameters, value)

    if isinstance(value, BaseModel):
        if len(parameters) == 1 and _parameter_accepts_model(parameters[0], value):
            parameter = parameters[0]
            return {
                parameter.name: _validate_value(
                    target,
                    parameter.name,
                    parameter.annotation,
                    value,
                )
            }

        return _bind_named_payload_for_parameters(target, parameters, value.model_dump())

    if isinstance(value, tuple):
        return _bind_tuple_for_parameters(target, parameters, value)

    return _bind_scalar_for_parameters(target, parameters, value)


def _bind_named_payload_for_parameters(
    target: Task,
    parameters: tuple[inspect.Parameter, ...],
    value: dict[str, Any],
) -> dict[str, Any]:
    bound: dict[str, Any] = {}
    missing: list[str] = []

    for parameter in parameters:
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


def _bind_tuple_for_parameters(
    target: Task,
    parameters: tuple[inspect.Parameter, ...],
    value: tuple[Any, ...],
) -> dict[str, Any]:
    if len(value) != len(parameters):
        raise TypeError(
            f"Cannot bind tuple output of length {len(value)} to task '{target.name}' "
            f"with {len(parameters)} parameters."
        )

    return {
        parameter.name: _validate_value(
            target,
            parameter.name,
            parameter.annotation,
            item,
        )
        for parameter, item in zip(parameters, value, strict=True)
    }


def _bind_scalar_for_parameters(
    target: Task,
    parameters: tuple[inspect.Parameter, ...],
    value: Any,
) -> dict[str, Any]:
    if len(parameters) != 1:
        raise TypeError(
            f"Cannot bind input of type {type(value).__name__} to "
            f"task '{target.name}' automatically."
        )

    parameter = parameters[0]
    return {
        parameter.name: _validate_value(
            target,
            parameter.name,
            parameter.annotation,
            value,
        )
    }


def _bind_named_payload(target: Task, value: dict[str, Any]) -> dict[str, Any]:
    return _bind_named_payload_for_parameters(target, target.parameters, value)


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


def _parameter_accepts_model(
    parameter: inspect.Parameter,
    value: BaseModel,
) -> bool:
    annotation = parameter.annotation
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


def _parameter_by_name(target: Task, parameter_name: str) -> inspect.Parameter:
    for parameter in target.parameters:
        if parameter.name == parameter_name:
            return parameter
    raise KeyError(
        f"Task '{target.name}' does not define a parameter named '{parameter_name}'."
    )
