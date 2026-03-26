import asyncio
import inspect
from typing import Any, Callable

from .node import Node


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

    async def run(self, **input: Any) -> Any:
        target = self.start.run if isinstance(self.start, Node) else self.start
        task_name = getattr(target, "__name__", repr(target))

        if getattr(target, "__elan_task__", False) is not True:
            raise TypeError(
                f"Workflow '{self.name}' expects tasks decorated with @task; "
                f"got '{task_name}'."
            )

        if inspect.iscoroutinefunction(target):
            task = target(**input)
        else:
            task = asyncio.to_thread(target, **input)

        return await task
