from __future__ import annotations

import inspect
from collections.abc import Mapping
from typing import Any, Callable, ClassVar, Generic, Literal, TypeVar

from pydantic import BaseModel

from .task import Task

ContextT = TypeVar("ContextT", bound=BaseModel)


class Binder(dict[str, Any], Generic[ContextT]):
    """Keyword binding wrapper that validates keys against a declared target."""

    model_cls: ClassVar[type[BaseModel] | None] = None
    target_task: ClassVar[Task | None] = None
    target_callable: ClassVar[Callable[..., Any] | None] = None
    target_fields: ClassVar[frozenset[str] | None] = None
    target_kind: ClassVar[Literal["model", "task"] | None] = None
    target_name: ClassVar[str | None] = None

    def __init__(
        self,
        mapping: Mapping[str, Any] | None = None,
        /,
        **kwargs: Any,
    ) -> None:
        data: dict[str, Any] = {}
        if mapping is not None:
            data.update(mapping)
        data.update(kwargs)
        self._validate_keys(data)
        super().__init__(data)

    @classmethod
    def __class_getitem__(cls, item: Any) -> type[Binder[Any]]:
        if isinstance(item, TypeVar):
            return super().__class_getitem__(item)
        if isinstance(item, tuple):
            raise TypeError(f"{cls.__name__}[...] accepts exactly one target.")

        namespace: dict[str, Any]
        if isinstance(item, type) and issubclass(item, BaseModel):
            namespace = {
                "model_cls": item,
                "target_fields": frozenset(item.model_fields),
                "target_kind": "model",
                "target_name": item.__name__,
            }
        elif isinstance(item, Task):
            namespace = {
                "target_task": item,
                "target_callable": item.fn,
                "target_fields": frozenset(parameter.name for parameter in item.parameters),
                "target_kind": "task",
                "target_name": item.name,
            }
        elif callable(item):
            namespace = {
                "target_callable": item,
                "target_fields": frozenset(_callable_parameter_names(item)),
                "target_kind": "task",
                "target_name": item.__name__,
            }
        else:
            raise TypeError(
                f"{cls.__name__}[...] requires a Pydantic model class, task, or callable."
            )

        return type(
            f"{cls.__name__}[{namespace['target_name']}]",
            (cls,),
            {
                "__module__": cls.__module__,
                **namespace,
            },
        )

    @classmethod
    def _validate_keys(cls, data: Mapping[str, Any]) -> None:
        if cls.target_fields is None:
            return

        unknown = [key for key in data if key not in cls.target_fields]
        if unknown:
            if cls.target_kind == "task":
                raise TypeError(
                    f"Task '{cls.target_name}' does not define parameters: "
                    f"{', '.join(unknown)}."
                )
            raise TypeError(
                f"Context model '{cls.target_name}' does not define fields: "
                f"{', '.join(unknown)}."
            )

    def matches_task(self, task: Task) -> bool:
        if self.target_kind != "task":
            return True
        return self.target_task is task or self.target_callable is task.fn


def _callable_parameter_names(fn: Callable[..., Any]) -> tuple[str, ...]:
    try:
        signature = inspect.signature(fn)
    except (TypeError, ValueError) as exc:
        raise TypeError(
            "Binder[...] requires a Pydantic model class, task, or callable."
        ) from exc
    return tuple(
        parameter.name
        for parameter in signature.parameters.values()
        if parameter.kind
        in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )
    )


class BindingDict(Binder[ContextT]):
    """Compatibility alias for keyword-only ``Binder[...]`` declarations."""


__all__ = ["Binder", "BindingDict"]
