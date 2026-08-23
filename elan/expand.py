from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, get_type_hints

from pydantic import TypeAdapter

from .fragment import Fragment
from .task import Task


@dataclass(frozen=True, slots=True)
class Expand:
    """A validated runtime-fragment builder used as a node's complete ``next``."""

    builder: Callable[[Any], Fragment]
    parameter_annotation: Any = field(repr=False)
    _input_adapter: TypeAdapter[Any] = field(repr=False, compare=False)

    def __init__(self, builder: Callable[[Any], Fragment]) -> None:
        annotation = _validate_builder(builder)
        try:
            adapter = TypeAdapter(annotation)
        except Exception as error:
            raise TypeError(
                "Expand builder parameter annotation is not runtime-validatable."
            ) from error
        object.__setattr__(self, "builder", builder)
        object.__setattr__(self, "parameter_annotation", annotation)
        object.__setattr__(self, "_input_adapter", adapter)


@dataclass(frozen=True, slots=True)
class _BoundExpand:
    expand: Expand
    lexical_scope: Mapping[str, str]


def _validate_builder(builder: Any) -> Any:
    if isinstance(builder, Task):
        raise TypeError("Expand requires a raw callable, not a @task object.")
    if not callable(builder):
        raise TypeError("Expand requires a synchronous raw callable.")
    if (
        inspect.iscoroutinefunction(builder)
        or inspect.isgeneratorfunction(builder)
        or inspect.isasyncgenfunction(builder)
    ):
        raise TypeError("Expand builder must be synchronous and non-generator.")

    try:
        signature = inspect.signature(builder)
    except (TypeError, ValueError) as error:
        raise TypeError("Expand builder must expose an inspectable signature.") from error

    parameters = tuple(signature.parameters.values())
    if len(parameters) != 1 or parameters[0].kind not in (
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    ):
        raise TypeError(
            "Expand builder must declare exactly one positional parameter."
        )
    if parameters[0].annotation is inspect.Parameter.empty:
        raise TypeError("Expand builder parameter must be annotated.")
    if signature.return_annotation is inspect.Signature.empty:
        raise TypeError("Expand builder must declare a -> Fragment return annotation.")

    try:
        hints = get_type_hints(builder)
    except (NameError, TypeError) as error:
        raise TypeError("Expand builder annotations could not be resolved.") from error

    parameter_annotation = hints.get(
        parameters[0].name,
        parameters[0].annotation,
    )
    return_annotation = hints.get("return", signature.return_annotation)
    if return_annotation is not Fragment:
        raise TypeError("Expand builder return annotation must be Fragment.")
    return parameter_annotation


__all__ = ["Expand"]
