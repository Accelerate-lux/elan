"""Prospective Elan API for a provider-agnostic agent/tool loop.

This is intentionally a design sketch, not a runnable example against the
current package.  It assumes the proposed primitives already exist and shows
both the explicit workflow and the higher-level ``AgentLoop`` that compiles to
the same graph.
"""

import asyncio
import os

import typer

from elan import (
    AgentLoop,
    Answer,
    Calls,
    Conversation,
    Emit,
    ModelCall,
    Node,
    Receive,
    ToolCall,
    ToolSet,
    UserMessage,
    Workflow,
    WorkflowPolicy,
    task,
    tool,
)
from elan.adapters.openai import OpenAIResponses


DEFAULT_MODEL = "gpt-5.6"
INSTRUCTIONS = (
    "Use the available arithmetic tools for every calculation. "
    "Use additional tool calls when a result requires multiple operations."
)

app = typer.Typer(add_completion=False)


# A tool remains an ordinary schedulable Elan task. The decorator only adds
# its model-facing name, description, and input/output schemas.
@tool
async def add(left: float, right: float) -> float:
    """Add two numbers."""
    return left + right


@tool
async def multiply(left: float, right: float) -> float:
    """Multiply two numbers."""
    return left * right


@task
async def initialize() -> Conversation:
    """Create the durable, provider-neutral state for one conversation."""
    return Conversation()


arithmetic_tools = ToolSet(add, multiply)

# The adapter translates canonical Elan requests, tool definitions, calls,
# and results to one provider protocol. It never schedules or executes tools.
model = OpenAIResponses(model=DEFAULT_MODEL)


# Low-level form. The workflow is a long-lived interaction loop:
#
#   initialize -> receive_user -> model -> emit_answer -> receive_user
#                                  ^  |
#                                  |  v
#                                call_tools
#
# Receive suspends the workflow until its handle is sent a UserMessage. Emit
# publishes an Answer without terminating the workflow. ModelCall returns
# Answer | Calls; ToolCall expands Calls into normal task activations, joins
# their correlated results, and resumes the model node.
explicit_tool_loop = Workflow(
    "arithmetic_tool_loop",
    policy=WorkflowPolicy(max_concurrency=4),
    start=Node(run=initialize, next="receive_user"),
    receive_user=Receive(UserMessage, next="model"),
    model=Node(
        run=ModelCall(
            model=model,
            instructions=INSTRUCTIONS,
            tools=arithmetic_tools,
            parallel_tool_calls=True,
        ),
        route_on=Answer | Calls,
        next={
            Answer: "emit_answer",
            Calls: "call_tools",
        },
    ),
    call_tools=ToolCall(
        tools=arithmetic_tools,
        next="model",
    ),
    emit_answer=Emit(Answer, next="receive_user"),
)


# High-level form. AgentLoop owns no new execution semantics: it compiles to
# the explicit workflow above and exposes its graph, events, and run state.
arithmetic_agent = AgentLoop(
    "arithmetic_agent",
    start=initialize,
    input=UserMessage,
    output=Answer,
    model=model,
    instructions=INSTRUCTIONS,
    tools=arithmetic_tools,
    parallel_tool_calls=True,
    max_model_steps=8,
    policy=WorkflowPolicy(max_concurrency=4),
)


async def run_cli(message: str | None) -> None:
    if "OPENAI_API_KEY" not in os.environ:
        typer.echo("Set OPENAI_API_KEY before running this example.", err=True)
        raise typer.Exit(code=2)

    # Starting the workflow runs initialization and suspends at Receive. The
    # application only transports inputs and outputs through the live handle;
    # both the user interaction and model/tool cycles belong to the workflow.
    async with arithmetic_agent.start() as run:
        if message is not None and message.strip():
            await run.send(UserMessage(text=message.strip()))
            answer = await run.receive(Answer)
            typer.echo(answer.text)
            return

        typer.echo("Enter /quit to stop.")
        while True:
            try:
                user_message = typer.prompt("you", prompt_suffix="> ").strip()
            except (EOFError, KeyboardInterrupt, typer.Abort):
                typer.echo()
                return
            if user_message == "/quit":
                return
            if not user_message:
                continue

            await run.send(UserMessage(text=user_message))
            answer = await run.receive(Answer)
            typer.echo(f"agent> {answer.text}")


@app.command()
def main(
    message: str | None = typer.Argument(
        None,
        help="One user message. Omit it to start the interactive loop.",
    ),
) -> None:
    """Run the prospective provider-agnostic agent loop."""
    asyncio.run(run_cli(message))


if __name__ == "__main__":
    app()
