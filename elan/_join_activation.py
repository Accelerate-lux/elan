import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from pydantic import BaseModel

from ._activation import ActivationStatus
from ._binding import bind_input
from ._refs import RefLookup
from .join import Join
from .policy import WorkflowPolicy
from .task import Task


@dataclass(slots=True)
class JoinActivation:
    id: str
    branch_id: str
    node_name: str
    join: Join
    join_instance_id: str
    reducer: Task | None
    input_value: list[Any]
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
        policy: WorkflowPolicy | None,
        on_yield: Callable[[Any], Awaitable[None]] | None = None,
    ) -> Any:
        del on_yield
        if self.reducer is None:
            self.output = list(self.input_value)
            return self.output

        lookup = RefLookup(
            workflow_input=workflow_input,
            context=context,
            policy=policy,
            upstream_value=self.input_value,
        )
        args, kwargs = bind_input(
            self.reducer,
            self.input_value,
            lookup=lookup,
        )
        if self.reducer.is_async:
            execution = self.reducer.fn(*args, **kwargs)
        else:
            execution = asyncio.to_thread(self.reducer.fn, *args, **kwargs)
        self.output = await execution
        return self.output
