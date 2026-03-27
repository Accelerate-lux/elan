import asyncio
import inspect
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, TypeAdapter, ValidationError

from .node import Node
from .result import WorkflowRun
from .task import Task, resolve_task, task


@dataclass(frozen=True)
class _MappedPayload:
    values: dict[str, Any]


class Workflow:
    def __init__(
        self,
        name: str,
        start: Task | str | Node,
        **nodes: Task | str | Node,
    ) -> None:
        self.name = name
        self.start = start
        self.nodes = nodes

    async def run(self, **input: Any) -> WorkflowRun:
        current = self.start
        current_input: Any = input
        result: dict[str, list[Any]] = {}

        while True:
            node = self._resolve_node(current)
            if current is self.start:
                args, kwargs = self._bind_entry_input(node.run, current_input)
            else:
                args, kwargs = self._bind_input(node.run, current_input)

            if node.run.is_async:
                execution = node.run.fn(*args, **kwargs)
            else:
                execution = asyncio.to_thread(node.run.fn, *args, **kwargs)

            output = await execution
            result.setdefault(node.run.name, []).append(output)

            if node.next is None:
                return WorkflowRun(result=result)

            if not isinstance(node.next, str):
                raise NotImplementedError(
                    "Only single-string routing is implemented in the initial scaffold."
                )

            if node.next not in self.nodes:
                raise KeyError(
                    f"Workflow '{self.name}' references unknown node '{node.next}'."
                )

            current = self.nodes[node.next]
            current_input = self._map_output(node, output)

    def _resolve_node(self, value: Task | str | Node) -> Node:
        if isinstance(value, Node):
            return Node(
                run=self._resolve_task_ref(value.run),
                next=value.next,
                input=value.input,
                output=value.output,
                route_on=value.route_on,
            )

        return Node(run=self._resolve_task_ref(value))

    def _resolve_task_ref(self, value: Task | str) -> Task:
        if isinstance(value, Task):
            return value

        if callable(value):
            raise TypeError(
                f"Workflow '{self.name}' expects tasks decorated with @task or registered task names; "
                f"got raw callable '{getattr(value, '__name__', repr(value))}'."
            )

        return resolve_task(value)

    def _bind_entry_input(self, target: Task, value: dict[str, Any]) -> tuple[tuple[Any, ...], dict[str, Any]]:
        return (), self._bind_named_payload(target, value)

    def _bind_input(self, target: Task, value: Any) -> tuple[tuple[Any, ...], dict[str, Any]]:
        if isinstance(value, _MappedPayload):
            return (), self._bind_named_payload(target, value.values)

        if isinstance(value, BaseModel):
            return self._bind_model_payload(target, value)

        if isinstance(value, tuple):
            return self._bind_tuple_payload(target, value)

        return self._bind_scalar_payload(target, value)

    def _bind_named_payload(self, target: Task, value: dict[str, Any]) -> dict[str, Any]:
        bound: dict[str, Any] = {}
        missing: list[str] = []

        for parameter in target.parameters:
            if parameter.name in value:
                bound[parameter.name] = self._validate_value(
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

    def _bind_model_payload(self, target: Task, value: BaseModel) -> tuple[tuple[Any, ...], dict[str, Any]]:
        if self._expects_model_instance(target, value):
            return (value,), {}

        return (), self._bind_named_payload(target, value.model_dump())

    def _expects_model_instance(self, target: Task, value: BaseModel) -> bool:
        if len(target.parameters) != 1:
            return False

        annotation = target.parameters[0].annotation
        if annotation is inspect.Signature.empty:
            return False

        try:
            return isinstance(value, annotation)
        except TypeError:
            return False

    def _bind_tuple_payload(self, target: Task, value: tuple[Any, ...]) -> tuple[tuple[Any, ...], dict[str, Any]]:
        if len(value) != len(target.parameters):
            raise TypeError(
                f"Cannot bind tuple output of length {len(value)} to task '{target.name}' "
                f"with {len(target.parameters)} parameters."
            )

        bound = tuple(
            self._validate_value(target, parameter.name, parameter.annotation, item)
            for parameter, item in zip(target.parameters, value, strict=True)
        )
        return bound, {}

    def _bind_scalar_payload(self, target: Task, value: Any) -> tuple[tuple[Any, ...], dict[str, Any]]:
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
                self._validate_value(
                    target,
                    parameter.name,
                    parameter.annotation,
                    value,
                ),
            ),
            {},
        )

    def _validate_value(
        self,
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

    def _map_output(self, node: Node, output: Any) -> Any:
        if node.output is None:
            return output

        names = [node.output] if isinstance(node.output, str) else node.output
        values = output if isinstance(output, (tuple, list)) else (output,)
        mapped: dict[str, Any] = {}
        for index, name in enumerate(names):
            if index >= len(values):
                break
            if name in (None, Ellipsis):
                continue
            mapped[str(name)] = values[index]
        return _MappedPayload(mapped)


__all__ = ["Workflow", "task"]
