# ruff: noqa: PIE794
"""Prospective Elan API for a provider-agnostic agent/tool loop.

This is intentionally a design sketch, not a runnable example against the
current package.  It assumes the proposed primitives already exist and shows
both the explicit workflow and the higher-level ``AgentLoop`` that compiles to
the same graph.
"""

import asyncio
import os
from collections.abc import AsyncIterator

import typer

from elan import (
    AgentLoop,
    Answer,
    Calls,
    Conversation,
    ModelCall,
    Node,
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
async def initialize(conversation: Conversation) -> None:
    """Initialize the durable, provider-neutral conversation context."""


@task
async def receive_user_message(
    inputs: AsyncIterator[UserMessage],
) -> UserMessage:
    """Consume exactly one packet from the workflow's open input."""
    return await anext(inputs)


arithmetic_tools = ToolSet(add, multiply)

# The adapter translates canonical Elan requests, tool definitions, calls,
# and results to one provider protocol. It never schedules or executes tools.
openai_model = OpenAIResponses(model=DEFAULT_MODEL)


# Low-level form. The workflow is a long-lived interaction loop:
#
#   initialize -> receive_user -> model_step
#   model_step -- Answer --> Workflow.output + receive_user
#   model_step -- Calls  --> call_tools --> model_step
#
# receive_user is an ordinary activation consuming one item from the open
# Workflow.input. It suspends without occupying an executor. ModelCall returns
# Answer | Calls. Answer is published through Workflow.output while control
# schedules the next receive activation; ToolCall expands Calls into ordinary
# task activations and resumes the model node.
class ArithmeticToolLoop(Workflow):
    receive_user: Node
    model_step: Node
    call_tools: ToolCall

    name = "arithmetic_tool_loop"
    input = UserMessage
    output = Answer
    context = Conversation
    policy = WorkflowPolicy(max_parallel_tasks=4)

    start = Node(run=initialize, next=receive_user)
    receive_user = Node(
        run=receive_user_message,
        input=Workflow.input,
        next=model_step,
    )
    model_step = Node(
        run=ModelCall(
            model=openai_model,
            instructions=INSTRUCTIONS,
            tools=arithmetic_tools,
            parallel_tool_calls=True,
        ),
        output={Answer: Workflow.output},
        next={
            Answer: receive_user,
            Calls: call_tools,
        },
    )
    call_tools = ToolCall(
        tools=arithmetic_tools,
        next=model_step,
    )


explicit_tool_loop = ArithmeticToolLoop()


# High-level form. AgentLoop owns no new execution semantics: its subclass
# declaration compiles to the explicit workflow above and exposes the same
# graph, open input/output boundary, events, and run state.
class ArithmeticAgent(AgentLoop):
    name = "arithmetic_agent"
    start = initialize
    input = UserMessage
    output = Answer
    context = Conversation
    model = openai_model
    instructions = INSTRUCTIONS
    tools = arithmetic_tools
    parallel_tool_calls = True
    max_model_steps = 8
    policy = WorkflowPolicy(max_parallel_tasks=4)


arithmetic_agent = ArithmeticAgent()


async def run_cli(message: str | None) -> None:
    if "OPENAI_API_KEY" not in os.environ:
        typer.echo("Set OPENAI_API_KEY before running this example.", err=True)
        raise typer.Exit(code=2)

    # Starting the workflow runs initialization and suspends the receive_user
    # activation on Workflow.input. The application only supplies and consumes
    # boundary values; both interaction cycles belong to the workflow.
    async with arithmetic_agent.start() as run:
        if message is not None and message.strip():
            await run.input(UserMessage(text=message.strip()))
            answer = await run.output(Answer)
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

            await run.input(UserMessage(text=user_message))
            answer = await run.output(Answer)
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
