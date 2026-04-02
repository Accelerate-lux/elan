import asyncio
from typing import Any

from ._binding import bind_entry_input, bind_input, map_output
from ._resolution import resolve_node
from ._routing import resolve_linear_next
from .node import Node
from .result import WorkflowRun
from .task import Task, task


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
            node = resolve_node(self.name, current)
            if current is self.start:
                args, kwargs = bind_entry_input(node.run, current_input)
            else:
                args, kwargs = bind_input(node.run, current_input)

            if node.run.is_async:
                execution = node.run.fn(*args, **kwargs)
            else:
                execution = asyncio.to_thread(node.run.fn, *args, **kwargs)

            output = await execution
            result.setdefault(node.run.name, []).append(output)

            next_node = resolve_linear_next(self.name, node.next, self.nodes)
            if next_node is None:
                return WorkflowRun(result=result)

            current = next_node
            current_input = map_output(node.output, output)


__all__ = ["Workflow", "task"]
