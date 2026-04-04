import asyncio
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ._activation import Activation

if TYPE_CHECKING:
    from ._orchestrator import Orchestrator


@dataclass(slots=True)
class SchedulerState:
    queued: deque[str] = field(default_factory=deque)
    running: dict[str, asyncio.Task[Any]] = field(default_factory=dict)
    settled: deque[str] = field(default_factory=deque)

    def enqueue(self, activation_id: str) -> None:
        self.queued.append(activation_id)

    def dequeue_queued(self) -> str | None:
        if not self.queued:
            return None
        return self.queued.popleft()

    def mark_running(
        self,
        activation_id: str,
        task: asyncio.Task[Any],
    ) -> None:
        self.running[activation_id] = task

    def mark_settled(self, activation_id: str) -> None:
        self.running.pop(activation_id, None)
        self.settled.append(activation_id)

    def activation_id_for_task(
        self,
        completed_task: asyncio.Task[Any],
    ) -> str:
        for activation_id, running_task in self.running.items():
            if running_task is completed_task:
                return activation_id
        raise KeyError("Completed task does not belong to any running activation.")

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

    def settle(self, activation: Activation) -> None:
        activation.mark_settled()
        self.state.mark_settled(activation.id)

    def next_settled(self) -> Activation | None:
        activation_id = self.state.dequeue_settled()
        if activation_id is None:
            return None
        return self.orchestrator.activation_for_id(activation_id)

    def launch_ready(self) -> None:
        while True:
            activation_id = self.state.dequeue_queued()
            if activation_id is None:
                return

            activation = self.orchestrator.activation_for_id(activation_id)
            activation.mark_running()
            task = asyncio.create_task(self.execute_activation(activation))
            self.state.mark_running(activation.id, task)

    async def execute_activation(
        self,
        activation: Activation,
    ) -> None:
        await activation.execute(
            workflow_input=self.orchestrator.run_state.workflow_input,
            context=self.orchestrator.run_state.context,
        )

    async def wait_next_completed(self) -> Activation | None:
        if not self.state.running:
            return None

        done, _pending = await asyncio.wait(
            set(self.state.running.values()),
            return_when=asyncio.FIRST_COMPLETED,
        )
        self._settle_completed(done)
        return self.next_settled()

    def _settle_completed(
        self,
        completed_tasks: set[asyncio.Task[Any]],
    ) -> None:
        for completed_task in completed_tasks:
            activation_id = self.state.activation_id_for_task(completed_task)
            completed_task.result()
            activation = self.orchestrator.activation_for_id(activation_id)
            self.settle(activation)

    async def update(self) -> Activation | None:
        settled = self.next_settled()
        if settled is not None:
            return settled

        self.launch_ready()
        if not self.state.running:
            if self.is_quiescent():
                return None
            raise RuntimeError(
                f"Workflow '{self.orchestrator.run_state.workflow.name}' reached a "
                "non-quiescent state without queued or running activations."
            )

        return await self.wait_next_completed()

    def is_quiescent(self) -> bool:
        return self.state.is_quiescent()
