from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel


@dataclass(frozen=True)
class SourceFieldRef:
    source: Literal["upstream", "input", "context"]
    field_name: str


@dataclass(frozen=True)
class ModelFieldRef:
    model: type[Any]
    field_name: str


class _SourceNamespace:
    def __init__(self, source: Literal["upstream", "input", "context"]) -> None:
        self._source = source

    def __getattr__(self, name: str) -> SourceFieldRef:
        if name.startswith("_"):
            raise AttributeError(name)
        return SourceFieldRef(source=self._source, field_name=name)


Upstream = _SourceNamespace("upstream")
Input = _SourceNamespace("input")
Context = _SourceNamespace("context")


_REFS_BY_NAME: dict[str, type[Any]] = {}


def register_ref(model: type[Any]) -> type[Any]:
    if not isinstance(model, type) or not issubclass(model, BaseModel):
        raise TypeError("@ref can only register Pydantic model classes.")

    name = model.__name__
    existing = _REFS_BY_NAME.get(name)
    if existing is not None and existing is not model:
        raise ValueError(f"Ref '{name}' is already registered.")

    _REFS_BY_NAME[name] = model

    for field_name in model.model_fields:
        setattr(model, field_name, ModelFieldRef(model=model, field_name=field_name))

    return model


def ref(model: type[Any]) -> type[Any]:
    return register_ref(model)


def resolve_ref(value: type[Any] | str) -> type[Any]:
    if isinstance(value, str):
        if value not in _REFS_BY_NAME:
            raise KeyError(f"Unknown ref '{value}'.")
        return _REFS_BY_NAME[value]
    return value


__all__ = ["Context", "Input", "Upstream", "ref", "resolve_ref"]
