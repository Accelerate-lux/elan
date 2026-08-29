"""Addressed reactive peer workflows using only existing Elan capabilities.

This is intentionally a one-off diagnostic prototype. It does not add an Elan
mailbox, event, listener, or workflow-handle abstraction. Instead, it combines:

* an application-owned dictionary of bounded ``asyncio.Queue`` mailboxes;
* an existing Elan async-generator task as the listening source;
* yielded packets for ordinary Elan routing and concurrent branch creation;
* a terminal mailbox item that exhausts the generator and lets the workflow's
  existing join and completion behavior drain outstanding work.

Install the example dependency and run the scripted peer exchange with:

    pip install -e ".[examples]"
    python examples/reactive_peer_workflows.py "What did peer messaging reveal?"

The code deliberately leaves address resolution, delivery, observation, and
shutdown outside Elan. Those seams are the requirements this prototype is
intended to expose.
"""

import asyncio
from collections.abc import AsyncIterator
from typing import Literal
from uuid import uuid4

import typer
from pydantic import BaseModel

from elan import Join, Node, Workflow, WorkflowPolicy, ref, task


app = typer.Typer(add_completion=False)


@ref
class PeerEvent(BaseModel):
    """One application-level envelope transported through a peer mailbox."""

    kind: Literal["ask", "request", "reply"]
    event_id: str
    correlation_id: str
    sender: str
    recipient: str
    text: str
    target: str | None = None


class StopListening(BaseModel):
    """One-off terminal mailbox item; it is not propagated downstream."""

    reason: str


class HandlingResult(BaseModel):
    peer: str
    action: Literal["request_sent", "reply_sent", "reply_observed"]
    event_id: str
    correlation_id: str
    text: str


MailboxItem = PeerEvent | StopListening

# These globals are deliberate application-side substitutes for missing Elan
# runtime contracts. They make the prototype runnable while keeping every gap
# visible in one file.
_mailboxes: dict[str, asyncio.Queue[MailboxItem]] = {}
_observed_replies: asyncio.Queue[PeerEvent] | None = None
_handler_delay_seconds = 0.0


def _new_event(
    *,
    kind: Literal["ask", "request", "reply"],
    correlation_id: str,
    sender: str,
    recipient: str,
    text: str,
    target: str | None = None,
) -> PeerEvent:
    return PeerEvent(
        kind=kind,
        event_id=f"event-{uuid4().hex[:12]}",
        correlation_id=correlation_id,
        sender=sender,
        recipient=recipient,
        text=text,
        target=target,
    )


async def _deliver(event: PeerEvent) -> None:
    """Application-owned addressing and backpressure, invisible to Elan."""
    mailbox = _mailboxes.get(event.recipient)
    if mailbox is None:
        raise RuntimeError(f"Unknown workflow address {event.recipient!r}.")
    await mailbox.put(event)
    typer.echo(
        f"transport> {event.kind} {event.event_id}: "
        f"{event.sender} -> {event.recipient}"
    )


async def _close(address: str, *, reason: str) -> None:
    mailbox = _mailboxes.get(address)
    if mailbox is None:
        raise RuntimeError(f"Unknown workflow address {address!r}.")
    await mailbox.put(StopListening(reason=reason))


@task
async def listen(address: str) -> AsyncIterator[PeerEvent]:
    """Keep one workflow source open and yield every accepted peer event."""
    mailbox = _mailboxes.get(address)
    if mailbox is None:
        raise RuntimeError(f"No mailbox was registered for {address!r}.")

    typer.echo(f"{address}> listener started")
    while True:
        # Today this await leaves the activation in `running`, retains a live
        # Python generator frame, and consumes one max_parallel_tasks slot.
        item = await mailbox.get()
        if isinstance(item, StopListening):
            typer.echo(f"{address}> listener closing: {item.reason}")
            return

        typer.echo(f"{address}> listener yielding {item.kind} {item.event_id}")
        yield item


@task
async def send_request(event: PeerEvent) -> HandlingResult:
    """Translate an external ask into a peer request as an opaque task effect."""
    if event.target is None:
        raise RuntimeError("An ask event requires a target peer address.")

    await asyncio.sleep(_handler_delay_seconds)
    request = _new_event(
        kind="request",
        correlation_id=event.correlation_id,
        sender=event.recipient,
        recipient=event.target,
        text=event.text,
    )
    await _deliver(request)
    return HandlingResult(
        peer=event.recipient,
        action="request_sent",
        event_id=request.event_id,
        correlation_id=request.correlation_id,
        text=request.text,
    )


@task
async def answer_request(event: PeerEvent) -> HandlingResult:
    """Reply through the one-off transport from inside an ordinary Elan task."""
    await asyncio.sleep(_handler_delay_seconds)
    reply = _new_event(
        kind="reply",
        correlation_id=event.correlation_id,
        sender=event.recipient,
        recipient=event.sender,
        text=f"{event.recipient} received: {event.text}",
    )
    await _deliver(reply)
    return HandlingResult(
        peer=event.recipient,
        action="reply_sent",
        event_id=reply.event_id,
        correlation_id=reply.correlation_id,
        text=reply.text,
    )


@task
async def observe_reply(event: PeerEvent) -> HandlingResult:
    """Expose completion to the CLI through another application side channel."""
    if _observed_replies is None:
        raise RuntimeError("The reply observation queue was not initialized.")

    await _observed_replies.put(event)
    # Keeping this branch active briefly lets the terminal event close the
    # listener before all emitted work has settled. The final Join must drain it.
    await asyncio.sleep(_handler_delay_seconds)
    return HandlingResult(
        peer=event.recipient,
        action="reply_observed",
        event_id=event.event_id,
        correlation_id=event.correlation_id,
        text=event.text,
    )


@task
def collect_results(results: list[HandlingResult]) -> list[HandlingResult]:
    return sorted(results, key=lambda result: (result.action, result.event_id))


def _peer_workflow(*, max_parallel_tasks: int) -> Workflow:
    return Workflow(
        "reactive_peer",
        policy=WorkflowPolicy(max_parallel_tasks=max_parallel_tasks),
        start=Node(
            run=listen,
            route_on=PeerEvent.kind,
            next={
                "ask": "send_request",
                "request": "answer_request",
                "reply": "observe_reply",
            },
        ),
        send_request=Node(run=send_request, next="result"),
        answer_request=Node(run=answer_request, next="result"),
        observe_reply=Node(run=observe_reply, next="result"),
        result=Join(run=collect_results),
    )


def _show_result(address: str, results: list[HandlingResult]) -> None:
    typer.echo(f"{address}> workflow completed with {len(results)} handled event(s)")
    for result in results:
        typer.echo(
            f"  {result.action}: correlation={result.correlation_id} "
            f"text={result.text!r}"
        )


async def run_demo(
    message: str,
    *,
    initiator: str,
    responder: str,
    mailbox_capacity: int,
    max_parallel_tasks: int,
    handler_delay_seconds: float,
    timeout_seconds: float,
) -> None:
    global _handler_delay_seconds, _mailboxes, _observed_replies

    if initiator == responder:
        raise ValueError("The initiator and responder addresses must differ.")
    if mailbox_capacity < 1:
        raise ValueError("Mailbox capacity must be at least 1.")
    if max_parallel_tasks < 1:
        raise ValueError("max_parallel_tasks must be at least 1.")
    if handler_delay_seconds < 0:
        raise ValueError("Handler delay cannot be negative.")
    if timeout_seconds <= 0:
        raise ValueError("Timeout must be positive.")

    _handler_delay_seconds = handler_delay_seconds
    _mailboxes = {
        initiator: asyncio.Queue(maxsize=mailbox_capacity),
        responder: asyncio.Queue(maxsize=mailbox_capacity),
    }
    _observed_replies = asyncio.Queue(maxsize=mailbox_capacity)

    workflow = _peer_workflow(max_parallel_tasks=max_parallel_tasks)
    run_tasks = {
        initiator: asyncio.create_task(workflow.run(address=initiator)),
        responder: asyncio.create_task(workflow.run(address=responder)),
    }
    correlation_id = f"correlation-{uuid4().hex[:12]}"

    try:
        await _deliver(
            _new_event(
                kind="ask",
                correlation_id=correlation_id,
                sender="cli",
                recipient=initiator,
                target=responder,
                text=message,
            )
        )
        reply = await asyncio.wait_for(
            _observed_replies.get(),
            timeout=timeout_seconds,
        )
        typer.echo(f"cli> observed reply from {reply.sender}: {reply.text}")

        # Closing both listening sources permits their already-emitted branches
        # to drain into each workflow-wide Join before ordinary completion.
        await asyncio.gather(
            _close(initiator, reason="scripted exchange completed"),
            _close(responder, reason="scripted exchange completed"),
        )
        completed = await asyncio.gather(*run_tasks.values())
    except BaseException:
        for run_task in run_tasks.values():
            run_task.cancel()
        await asyncio.gather(*run_tasks.values(), return_exceptions=True)
        raise

    for address, run in zip(run_tasks, completed, strict=True):
        _show_result(address, run.result)


@app.command()
def main(
    message: str = typer.Argument(
        "Hello from one reactive workflow to another.",
        help="Message the initiator asks the responder to process.",
    ),
    initiator: str = typer.Option("alpha", help="Address of the initiating workflow."),
    responder: str = typer.Option("beta", help="Address of the responding workflow."),
    mailbox_capacity: int = typer.Option(
        8,
        min=1,
        help="Bound of each application-owned in-memory mailbox.",
    ),
    max_parallel_tasks: int = typer.Option(
        4,
        min=1,
        help="Per-workflow Elan concurrency limit; the listener currently consumes one slot.",
    ),
    handler_delay_seconds: float = typer.Option(
        0.05,
        min=0.0,
        help="Artificial delay that makes listener/handler overlap observable.",
    ),
    timeout_seconds: float = typer.Option(
        5.0,
        min=0.01,
        help="Maximum time to wait for the correlated reply.",
    ),
) -> None:
    """Run two addressed peer workflows through a scripted request/reply."""
    try:
        asyncio.run(
            run_demo(
                message,
                initiator=initiator,
                responder=responder,
                mailbox_capacity=mailbox_capacity,
                max_parallel_tasks=max_parallel_tasks,
                handler_delay_seconds=handler_delay_seconds,
                timeout_seconds=timeout_seconds,
            )
        )
    except (RuntimeError, ValueError, TimeoutError) as error:
        typer.echo(f"Prototype failed: {error}", err=True)
        raise typer.Exit(code=1) from error


if __name__ == "__main__":
    app()
