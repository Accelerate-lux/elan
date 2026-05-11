import inspect
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Task:
    key: str
    fn: Callable[..., Any]
    signature: inspect.Signature
    parameters: tuple[inspect.Parameter, ...]
    is_async: bool
    is_generator: bool
    is_async_generator: bool
    alias: str | None = None

    @property
    def name(self) -> str:
        return self.alias or self.fn.__name__


_TASKS_BY_KEY: dict[str, Task] = {}
_TASKS_BY_ALIAS: dict[str, Task] = {}


def _task_key(fn: Callable[..., Any]) -> str:
    return f"{fn.__module__}.{fn.__qualname__}"


def _create_task(fn: Callable[..., Any], *, alias: str | None = None) -> Task:
    key = _task_key(fn)
    signature = inspect.signature(fn)
    parameters = tuple(
        parameter
        for parameter in signature.parameters.values()
        if parameter.kind
        in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )
    )
    return Task(
        key=key,
        fn=fn,
        signature=signature,
        parameters=parameters,
        is_async=inspect.iscoroutinefunction(fn),
        is_generator=inspect.isgeneratorfunction(fn),
        is_async_generator=inspect.isasyncgenfunction(fn),
        alias=alias,
    )


def register_task(task: Task) -> Task:
    existing = _TASKS_BY_KEY.get(task.key)
    if existing is not None:
        if existing.fn is task.fn and existing.alias == task.alias:
            return existing
        raise ValueError(f"Task '{task.key}' is already registered.")

    if task.alias is not None:
        existing_alias = _TASKS_BY_ALIAS.get(task.alias)
        if existing_alias is not None:
            raise ValueError(
                f"Task alias '{task.alias}' is already registered for '{existing_alias.key}'."
            )
        _TASKS_BY_ALIAS[task.alias] = task

    _TASKS_BY_KEY[task.key] = task
    return task


def resolve_task(value: Task | str) -> Task:
    if isinstance(value, Task):
        return value

    if value in _TASKS_BY_KEY:
        return _TASKS_BY_KEY[value]

    if value in _TASKS_BY_ALIAS:
        return _TASKS_BY_ALIAS[value]

    raise KeyError(f"Unknown task '{value}'.")


def task(
    fn: Callable[..., Any] | None = None,
    *,
    alias: str | None = None,
) -> Task | Callable[[Callable[..., Any]], Task]:
    def _decorate(inner_fn: Callable[..., Any]) -> Task:
        return register_task(_create_task(inner_fn, alias=alias))

    if fn is None:
        return _decorate

    return _decorate(fn)
