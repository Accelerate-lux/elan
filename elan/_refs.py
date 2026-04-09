from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel


@dataclass(frozen=True)
class RefLookup:
    workflow_input: dict[str, Any]
    context: BaseModel | None
    upstream_value: Any

    def input_field(self, field_name: str, *, owner: str) -> Any:
        if field_name not in self.workflow_input:
            raise TypeError(
                f"Workflow input does not provide field '{field_name}' for {owner}."
            )
        return self.workflow_input[field_name]

    def context_field(self, field_name: str, *, owner: str) -> Any:
        if self.context is None:
            raise TypeError(f"{owner} cannot read Context.{field_name} without workflow context.")
        return resolve_model_field(
            self.context,
            field_name,
            source_name="Context",
            owner=owner,
        )

    def upstream_field(self, field_name: str, *, owner: str) -> Any:
        if self.upstream_value is None:
            raise TypeError(f"{owner} cannot read Upstream.{field_name} without upstream value.")
        return resolve_value_field(
            self.upstream_value,
            field_name,
            source_name="Upstream",
            owner=owner,
        )


@dataclass(frozen=True)
class SourceFieldRef:
    field_name: str

    def eval(self, lookup: RefLookup, *, owner: str) -> Any:
        raise NotImplementedError


@dataclass(frozen=True)
class InputFieldRef(SourceFieldRef):
    def eval(self, lookup: RefLookup, *, owner: str) -> Any:
        return lookup.input_field(self.field_name, owner=owner)


@dataclass(frozen=True)
class ContextFieldRef(SourceFieldRef):
    def eval(self, lookup: RefLookup, *, owner: str) -> Any:
        return lookup.context_field(self.field_name, owner=owner)


@dataclass(frozen=True)
class UpstreamFieldRef(SourceFieldRef):
    def eval(self, lookup: RefLookup, *, owner: str) -> Any:
        return lookup.upstream_field(self.field_name, owner=owner)


@dataclass(frozen=True)
class ModelFieldRef:
    model: type[Any]
    field_name: str


class _SourceNamespace:
    def __init__(self, ref_type: type[SourceFieldRef]) -> None:
        self._ref_type = ref_type

    def __getattr__(self, name: str) -> SourceFieldRef:
        if name.startswith("_"):
            raise AttributeError(name)
        return self._ref_type(field_name=name)


Upstream = _SourceNamespace(UpstreamFieldRef)
Input = _SourceNamespace(InputFieldRef)
Context = _SourceNamespace(ContextFieldRef)


def resolve_model_field(
    value: BaseModel,
    field_name: str,
    *,
    source_name: str,
    owner: str | None = None,
) -> Any:
    if field_name not in type(value).model_fields:
        if owner is None:
            raise TypeError(f"{source_name} does not provide field '{field_name}'.")
        raise TypeError(f"{source_name} does not provide field '{field_name}' for {owner}.")
    return getattr(value, field_name)


def resolve_value_field(
    value: Any,
    field_name: str,
    *,
    source_name: str,
    owner: str,
) -> Any:
    if isinstance(value, BaseModel):
        return resolve_model_field(
            value,
            field_name,
            source_name=source_name,
            owner=owner,
        )

    payload_values = getattr(value, "values", None)
    if isinstance(payload_values, dict):
        if field_name not in payload_values:
            raise TypeError(f"{source_name} payload does not provide field '{field_name}' for {owner}.")
        return payload_values[field_name]

    raise TypeError(
        f"{owner} cannot read {source_name}.{field_name} from value of type {type(value).__name__}."
    )


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


__all__ = [
    "Context",
    "Input",
    "Upstream",
    "ref",
    "resolve_ref",
    "RefLookup",
    "SourceFieldRef",
    "ModelFieldRef",
]
