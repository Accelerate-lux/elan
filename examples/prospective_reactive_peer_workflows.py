# ruff: noqa: PIE794
"""Prospective Elan API for addressable reactive peer workflows.

This is intentionally a design sketch, not a runnable example against the
current package. It explores a reactive extension of Elan's existing input and
output contracts without adding listener, messaging, or port graph elements.

The proposed semantic change is about lifetime and cardinality:

* a workflow input may remain open and supply several packets;
* a workflow output may publish several packets before final completion;
* an activation may suspend without retaining an executor;
* closing the input lets already-created branches drain before completion.

Nodes remain ordinary nodes. Tasks consume inputs and return or yield outputs.
Addressing, correlation, and causation are event data interpreted at the
workflow boundary, not alternate control-flow primitives.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import typer
from pydantic import BaseModel

from elan import (
    Address,
    Event,
    Node,
    Workflow,
    WorkflowPolicy,
    task,
)


app = typer.Typer(add_completion=False)


class Ask(BaseModel):
    """Tell one live workflow to contact another live workflow."""

    peer: Address
    text: str


class Request(BaseModel):
    text: str


class Reply(BaseModel):
    text: str


class ReplyObserved(BaseModel):
    """Application-visible output from the initiating workflow."""

    peer: Address
    text: str


class Shutdown(BaseModel):
    """Input value that exhausts the receiving activation."""

    reason: str


PeerInput = Ask | Request | Reply | Shutdown
PeerOutput = Event[Request | Reply] | ReplyObserved


@task
async def initialize() -> None:
    """Initialize peer-owned resources once before consuming live input."""


@task
async def receive_inputs(
    inputs: AsyncIterator[Event[PeerInput]],
) -> AsyncIterator[Event[Ask | Request | Reply]]:
    """Yield workflow inputs until a typed shutdown input closes the source."""
    async for event in inputs:
        if isinstance(event.payload, Shutdown):
            return
        yield event


@task
def make_request(event: Event[Ask]) -> Event[Request]:
    """Produce an addressed workflow output while preserving correlation."""
    return event.forward(
        to=event.payload.peer,
        payload=Request(text=event.payload.text),
    )


@task
def make_reply(event: Event[Request]) -> Event[Reply]:
    """Produce an output addressed to the request's recorded reply address."""
    return event.reply(
        payload=Reply(
            text=f"{event.recipient} received: {event.payload.text}",
        )
    )


@task
def make_observation(event: Event[Reply]) -> ReplyObserved:
    return ReplyObserved(peer=event.sender, text=event.payload.text)


# The graph contains only tasks and nodes:
#
#   initialize -> receive(workflow input)
#                    |
#                    +-- Ask -----> build request --+
#                    +-- Request -> build reply ----+--> workflow output
#                    +-- Reply ---> observe reply --+
#                    +-- Shutdown -> exhaust source
#
# receive is one generator activation. Each yielded input follows ordinary Elan
# routing and creates an ordinary branch. Directing a terminal node's output to
# Workflow.output publishes the packet and retires that branch. When receive
# exhausts, the source branch closes; yielded branches drain before the existing
# workflow completion rule can settle the run.
class ReactivePeer(Workflow):
    receive: Node
    build_request: Node
    build_reply: Node
    observe_reply: Node

    name = "reactive_peer"
    input = PeerInput
    output = PeerOutput
    policy = WorkflowPolicy(max_parallel_tasks=4)

    start = Node(run=initialize, next=receive)
    receive = Node(
        run=receive_inputs,
        input=Workflow.input,
        next={
            Ask: build_request,
            Request: build_reply,
            Reply: observe_reply,
        },
    )
    build_request = Node(
        run=make_request,
        output=Workflow.output,
    )
    build_reply = Node(
        run=make_reply,
        output=Workflow.output,
    )
    observe_reply = Node(
        run=make_observation,
        output=Workflow.output,
    )


reactive_peer = ReactivePeer()


async def run_cli(message: str, *, initiator: str, responder: str) -> None:
    alpha_address = Address(initiator)
    beta_address = Address(responder)

    # start(address=...) creates a live addressed run. input(...) appends a value
    # to that run's existing workflow input and returns its accepted Event.
    async with (
        reactive_peer.start(address=alpha_address) as alpha,
        reactive_peer.start(address=beta_address) as beta,
    ):
        sent = await alpha.input(Ask(peer=beta.address, text=message))

        # An addressed Event published through Workflow.output is delivered to
        # the target run's Workflow.input. A plain value remains available on
        # the producing run's Workflow.output. Both retain branch causality.
        observed = await alpha.output(
            ReplyObserved,
            correlation_id=sent.correlation_id,
        )
        typer.echo(f"{observed.peer}> {observed.text}")

        # Shutdown is ordinary workflow input. The receive task consumes it and
        # returns instead of yielding it, which closes the source activation.
        await asyncio.gather(
            alpha.input(Shutdown(reason="CLI exchange completed")),
            beta.input(Shutdown(reason="CLI exchange completed")),
        )

        # wait() observes normal completion after both source and descendant
        # branches have settled.
        await asyncio.gather(alpha.wait(), beta.wait())


@app.command()
def main(
    message: str = typer.Argument(
        "Hello from one reactive workflow to another.",
        help="Message the initiating workflow asks its peer to process.",
    ),
    initiator: str = typer.Option(
        "peer:alpha",
        help="Stable address of the initiating workflow.",
    ),
    responder: str = typer.Option(
        "peer:beta",
        help="Stable address of the responding workflow.",
    ),
) -> None:
    """Run the prospective addressed peer interaction."""
    asyncio.run(run_cli(message, initiator=initiator, responder=responder))


if __name__ == "__main__":
    app()
