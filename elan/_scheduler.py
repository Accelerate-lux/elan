import asyncio
from collections import deque
from dataclasses import dataclass, field

from ._activation import Activation
from ._binding import bind_entry_input, bind_input
from ._run_state import RunState


@dataclass(slots=True)
class SchedulerState:
    queued: deque[str] = field(default_factory=deque)
    running: set[str] = field(default_factory=set)
    settled: deque[str] = field(default_factory=deque)


@dataclass(slots=True)
class Scheduler:
    state: SchedulerState = field(default_factory=SchedulerState)

    def enqueue(self, activation: Activation) -> None:
        activation.status = "queued"
        self.state.queued.append(activation.id)

    def start_next(self, run_state: RunState) -> Activation | None:
        if not self.state.queued:
            return None
        activation_id = self.state.queued.popleft()
        activation = run_state.activations[activation_id]
        activation.status = "running"
        self.state.running.add(activation.id)
        return activation

    def settle(self, activation: Activation) -> None:
        activation.status = "settled"
        self.state.running.discard(activation.id)
        self.state.settled.append(activation.id)

    def next_settled(self, run_state: RunState) -> Activation | None:
        if not self.state.settled:
            return None
        activation_id = self.state.settled.popleft()
        return run_state.activations[activation_id]

    async def update(
        self,
        run_state: RunState,
    ) -> Activation | None:
        activation = self.start_next(run_state)
        if activation is None:
            if self.is_quiescent():
                return None
            raise RuntimeError(
                f"Workflow '{run_state.workflow.name}' reached a non-quiescent state without queued activations."
            )

        activation.output = await self._execute_activation(run_state, activation)
        self.settle(activation)
        return self.next_settled(run_state)

    async def _execute_activation(
        self,
        run_state: RunState,
        activation: Activation,
    ) -> object:
        if activation.is_entry:
            args, kwargs = bind_entry_input(
                activation.node.run,
                activation.input_value,
                input_spec=activation.node.bind_input,
                workflow_input=run_state.workflow_input,
                context_value=run_state.context_value,
            )
        else:
            args, kwargs = bind_input(
                activation.node.run,
                activation.input_value,
                input_spec=activation.node.bind_input,
                workflow_input=run_state.workflow_input,
                context_value=run_state.context_value,
            )

        if activation.node.run.is_async:
            execution = activation.node.run.fn(*args, **kwargs)
        else:
            execution = asyncio.to_thread(activation.node.run.fn, *args, **kwargs)

        return await execution

    def is_quiescent(self) -> bool:
        return (
            not self.state.queued
            and not self.state.running
            and not self.state.settled
        )
