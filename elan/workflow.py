import asyncio
import inspect
from typing import Any, Callable

from .node import Node
from .result import WorkflowRun


def task(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Register a callable as an Elan task."""
    setattr(fn, "__elan_task__", True)
    return fn


class Workflow:
    def __init__(
        self,
        name: str,
        start: Callable[..., Any] | Node,
        **nodes: Callable[..., Any] | Node,
    ) -> None:
        self.name = name
        self.start = start
        self.nodes = nodes

    async def run(self, **input: Any) -> WorkflowRun:
        current = self.start
        current_input: Any = input
        result: dict[str, list[Any]] = {}

        while True:
            node = current if isinstance(current, Node) else Node(run=current)
            target = node.run
            task_name = getattr(target, "__name__", repr(target))

            if getattr(target, "__elan_task__", False) is not True:
                raise TypeError(
                    f"Workflow '{self.name}' expects tasks decorated with @task; "
                    f"got '{task_name}'."
                )

            if inspect.iscoroutinefunction(target):
                task = target(**self._bind_input(target, current_input))
            else:
                task = asyncio.to_thread(target, **self._bind_input(target, current_input))

            output = await task
            result.setdefault(task_name, []).append(output)

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

    def _bind_input(self, target: Callable[..., Any], value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value

        parameters = [
            parameter
            for parameter in inspect.signature(target).parameters.values()
            if parameter.kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            )
        ]

        if not parameters:
            return {}

        if len(parameters) == 1:
            return {parameters[0].name: value}

        raise TypeError(
            f"Cannot bind input of type {type(value).__name__} to "
            f"task '{target.__name__}' automatically."
        )

    def _map_output(self, node: Node, output: Any) -> Any:
        if node.output is None:
            return output

        values = output if isinstance(output, (tuple, list)) else (output,)
        mapped: dict[str, Any] = {}
        for index, name in enumerate(node.output):
            if index >= len(values):
                break
            if name in (None, Ellipsis):
                continue
            mapped[str(name)] = values[index]
        return mapped
