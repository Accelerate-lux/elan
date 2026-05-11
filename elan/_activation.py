import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Literal

from pydantic import BaseModel

from ._binding import bind_entry_input, bind_input
from ._refs import RefLookup
from .node import Node

ActivationStatus = Literal["queued", "running", "settled"]
_GENERATOR_DONE = object()


@dataclass(slots=True)
class Activation:
    id: str
    branch_id: str
    node_name: str | None
    node: Node
    input_value: Any
    is_entry: bool
    status: ActivationStatus = "queued"
    output: Any = None
    yielded: bool = False

    def mark_queued(self) -> None:
        self.status = "queued"

    def mark_running(self) -> None:
        self.status = "running"

    def mark_settled(self) -> None:
        self.status = "settled"

    async def execute(
        self,
        *,
        workflow_input: dict[str, Any],
        context: BaseModel | None,
        on_yield: Callable[[Any], Awaitable[None]] | None = None,
    ) -> Any:
        lookup = RefLookup(
            workflow_input=workflow_input,
            context=context,
            upstream_value=None if self.is_entry else self.input_value,
        )
        if self.is_entry:
            args, kwargs = bind_entry_input(
                self.node.run,
                self.input_value,
                input_spec=self.node.bind_input,
                lookup=lookup,
            )
        else:
            args, kwargs = bind_input(
                self.node.run,
                self.input_value,
                input_spec=self.node.bind_input,
                lookup=lookup,
            )

        if self.node.run.is_async_generator:
            self.output = await self._execute_async_generator(args, kwargs, on_yield)
            return self.output

        if self.node.run.is_generator:
            self.output = await self._execute_sync_generator(args, kwargs, on_yield)
            return self.output

        if self.node.run.is_async:
            execution = self.node.run.fn(*args, **kwargs)
        else:
            execution = asyncio.to_thread(self.node.run.fn, *args, **kwargs)

        self.output = await execution
        return self.output

    async def _execute_async_generator(
        self,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        on_yield: Callable[[Any], Awaitable[None]] | None,
    ) -> list[Any]:
        self.yielded = True
        yielded_items: list[Any] = []
        async for item in self.node.run.fn(*args, **kwargs):
            yielded_items.append(item)
            if on_yield is not None:
                await on_yield(item)
        return yielded_items

    async def _execute_sync_generator(
        self,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        on_yield: Callable[[Any], Awaitable[None]] | None,
    ) -> list[Any]:
        self.yielded = True
        yielded_items: list[Any] = []
        iterator = self.node.run.fn(*args, **kwargs)
        while True:
            item = await asyncio.to_thread(_next_or_done, iterator)
            if item is _GENERATOR_DONE:
                return yielded_items
            yielded_items.append(item)
            if on_yield is not None:
                await on_yield(item)


def _next_or_done(iterator: Any) -> Any:
    try:
        return next(iterator)
    except StopIteration:
        return _GENERATOR_DONE
