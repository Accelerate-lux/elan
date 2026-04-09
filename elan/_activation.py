import asyncio
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel

from ._binding import bind_entry_input, bind_input
from ._refs import RefLookup
from .node import Node

ActivationStatus = Literal["queued", "running", "settled"]


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

        if self.node.run.is_async:
            execution = self.node.run.fn(*args, **kwargs)
        else:
            execution = asyncio.to_thread(self.node.run.fn, *args, **kwargs)

        self.output = await execution
        return self.output
