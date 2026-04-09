from __future__ import annotations

from typing import Any

from pydantic import BaseModel, TypeAdapter, ValidationError

from ._refs import ModelFieldRef, RefLookup, SourceFieldRef


def prepare_context(
    *,
    workflow_name: str,
    branch_context: BaseModel | None,
    mapping: dict[str, Any] | None,
    lookup: RefLookup,
    phase_name: str,
) -> BaseModel | None:
    if mapping is None:
        return branch_context

    if branch_context is None:
        raise TypeError(
            f"Workflow '{workflow_name}' cannot use {phase_name} without workflow context."
        )

    unknown = [
        context_key
        for context_key in mapping
        if context_key not in type(branch_context).model_fields
    ]
    if unknown:
        raise TypeError(
            f"Context model '{type(branch_context).__name__}' does not define fields: {', '.join(unknown)}."
        )

    updates = {
        context_key: resolve_context_value(
            workflow_name=workflow_name,
            branch_context=branch_context,
            context_key=context_key,
            value=value,
            lookup=lookup,
            phase_name=phase_name,
        )
        for context_key, value in mapping.items()
    }
    return merge_context(branch_context, updates)


def resolve_context_value(
    *,
    workflow_name: str,
    branch_context: BaseModel,
    context_key: str,
    value: Any,
    lookup: RefLookup,
    phase_name: str,
) -> Any:
    if isinstance(value, SourceFieldRef):
        resolved = value.eval(lookup, owner=phase_name)
    elif isinstance(value, ModelFieldRef):
        raise TypeError(
            f"Workflow '{workflow_name}' cannot use bare model field reference "
            f"'{value.model.__name__}.{value.field_name}' in {phase_name}; use Input/Context/Upstream refs instead."
        )
    else:
        resolved = value

    annotation = type(branch_context).model_fields[context_key].annotation
    if annotation is None:
        return resolved

    try:
        return TypeAdapter(annotation).validate_python(resolved)
    except ValidationError as exc:
        raise TypeError(
            f"Context value for field '{context_key}' in {phase_name} is not compatible with the declared schema."
        ) from exc


def merge_context(
    context: BaseModel,
    updates: dict[str, Any],
) -> BaseModel:
    model_cls = type(context)
    unknown = [
        field_name for field_name in updates if field_name not in model_cls.model_fields
    ]
    if unknown:
        raise TypeError(
            f"Context model '{model_cls.__name__}' does not define fields: {', '.join(unknown)}."
        )

    merged = {**context.model_dump(), **updates}
    try:
        return model_cls.model_validate(merged)
    except ValidationError as exc:
        raise TypeError(
            f"Context update for model '{model_cls.__name__}' is not compatible with the declared schema."
        ) from exc


def copy_context(context: BaseModel | None) -> BaseModel | None:
    if context is None:
        return None
    return context.model_copy(deep=True)
