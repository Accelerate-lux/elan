from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ._activation import Activation

if TYPE_CHECKING:
    from ._orchestrator import Orchestrator


@dataclass(slots=True)
class SchedulerState:
    queued: deque[str] = field(default_factory=deque)
    running: set[str] = field(default_factory=set)
    settled: deque[str] = field(default_factory=deque)

    def enqueue(self, activation_id: str) -> None:
        self.queued.append(activation_id)

    def dequeue_queued(self) -> str | None:
        if not self.queued:
            return None
        return self.queued.popleft()

    def mark_running(self, activation_id: str) -> None:
        self.running.add(activation_id)

    def mark_settled(self, activation_id: str) -> None:
        self.running.discard(activation_id)
        self.settled.append(activation_id)

    def dequeue_settled(self) -> str | None:
        if not self.settled:
            return None
        return self.settled.popleft()

    def is_quiescent(self) -> bool:
        return not self.queued and not self.running and not self.settled


@dataclass(slots=True)
class Scheduler:
    orchestrator: "Orchestrator"
    state: SchedulerState = field(default_factory=SchedulerState)

    def enqueue(self, activation: Activation) -> None:
        activation.mark_queued()
        self.state.enqueue(activation.id)

    def start_next(self) -> Activation | None:
        activation_id = self.state.dequeue_queued()
        if activation_id is None:
            return None
        activation = self.orchestrator.activation_for_id(activation_id)
        activation.mark_running()
        self.state.mark_running(activation.id)
        return activation

    def settle(self, activation: Activation) -> None:
        activation.mark_settled()
        self.state.mark_settled(activation.id)

    def next_settled(self) -> Activation | None:
        activation_id = self.state.dequeue_settled()
        if activation_id is None:
            return None
        return self.orchestrator.activation_for_id(activation_id)

    async def update(self) -> Activation | None:
        activation = self.start_next()
        if activation is None:
            if self.is_quiescent():
                return None
            raise RuntimeError(
                f"Workflow '{self.orchestrator.run_state.workflow.name}' reached a "
                "non-quiescent state without queued activations."
            )

        await self.orchestrator.execute_activation(activation)
        self.settle(activation)
        return self.next_settled()

    def is_quiescent(self) -> bool:
        return self.state.is_quiescent()
