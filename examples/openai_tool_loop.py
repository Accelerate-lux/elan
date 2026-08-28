"""OpenAI tool-call loop expressed only with Elan's existing primitives.

Install the optional dependency, export ``OPENAI_API_KEY``, then run:

    pip install -e ".[openai]"
    python examples/openai_tool_loop.py "Calculate (17 + 25) * 3"

With no message argument, the script starts a small multi-turn REPL. The outer
user/agent loop is ordinary application code; each user turn runs the Elan
workflow containing the model/tool loop.
"""

import asyncio
import json
import os
from typing import Any, Literal

import typer
from pydantic import BaseModel

from elan import Node, Workflow, WorkflowPolicy, ref, task


DEFAULT_MODEL = "gpt-5.6"
MAX_MODEL_STEPS = 8

app = typer.Typer(add_completion=False)

INSTRUCTIONS = (
    "Use the available arithmetic tools for every calculation. "
    "Use additional tool calls when a result requires multiple operations."
)

TOOLS = [
    {
        "type": "function",
        "name": "add",
        "description": "Add two numbers.",
        "parameters": {
            "type": "object",
            "properties": {
                "left": {"type": "number"},
                "right": {"type": "number"},
            },
            "required": ["left", "right"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "multiply",
        "description": "Multiply two numbers.",
        "parameters": {
            "type": "object",
            "properties": {
                "left": {"type": "number"},
                "right": {"type": "number"},
            },
            "required": ["left", "right"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


class AgentInput(BaseModel):
    model: str
    message: str | None = None
    previous_response_id: str | None = None
    tool_call_id: str | None = None
    tool_output: str | None = None
    model_steps: int = 0


@ref
class ModelStep(BaseModel):
    route: Literal["add", "multiply", "answer"]
    model: str
    response_id: str
    call_id: str | None = None
    arguments: str | None = None
    answer: str | None = None
    model_steps: int


class AgentReply(BaseModel):
    text: str
    response_id: str


class BinaryOperands(BaseModel):
    left: int | float
    right: int | float


_openai_client: Any | None = None


async def _create_response(**kwargs: Any) -> Any:
    """Thin, replaceable SDK boundary; it is not an Elan abstraction."""
    global _openai_client

    if _openai_client is None:
        try:
            from openai import AsyncOpenAI
        except ImportError as error:
            raise RuntimeError(
                'Install the prototype dependency with: pip install -e ".[openai]"'
            ) from error
        _openai_client = AsyncOpenAI(timeout=30.0, max_retries=1)

    return await _openai_client.responses.create(**kwargs)


@task
async def begin_turn(
    message: str,
    model: str = DEFAULT_MODEL,
    previous_response_id: str | None = None,
) -> AgentInput:
    return AgentInput(
        message=message,
        model=model,
        previous_response_id=previous_response_id,
    )


@task
async def reason(state: AgentInput) -> ModelStep:
    if state.model_steps >= MAX_MODEL_STEPS:
        raise RuntimeError(
            f"Model exceeded the prototype limit of {MAX_MODEL_STEPS} steps."
        )

    if state.tool_call_id is None:
        if state.message is None:
            raise RuntimeError("A model step requires a user message or tool output.")
        request_input: str | list[dict[str, str]] = state.message
    else:
        if state.tool_output is None:
            raise RuntimeError("A tool continuation requires a tool output.")
        request_input = [
            {
                "type": "function_call_output",
                "call_id": state.tool_call_id,
                "output": state.tool_output,
            }
        ]

    request: dict[str, Any] = {
        "model": state.model,
        "instructions": INSTRUCTIONS,
        "input": request_input,
        "tools": TOOLS,
        "parallel_tool_calls": False,
    }
    if state.previous_response_id is not None:
        request["previous_response_id"] = state.previous_response_id

    response = await _create_response(**request)
    calls = [
        item
        for item in response.output
        if getattr(item, "type", None) == "function_call"
    ]
    if len(calls) > 1:
        raise RuntimeError("The model returned parallel calls despite disabling them.")

    model_steps = state.model_steps + 1
    if calls:
        call = calls[0]
        return ModelStep(
            route=call.name,
            model=state.model,
            response_id=response.id,
            call_id=call.call_id,
            arguments=call.arguments,
            model_steps=model_steps,
        )

    if not response.output_text:
        raise RuntimeError("The model returned neither a function call nor text.")
    return ModelStep(
        route="answer",
        model=state.model,
        response_id=response.id,
        answer=response.output_text,
        model_steps=model_steps,
    )


def _tool_continuation(step: ModelStep, result: int | float) -> AgentInput:
    if step.call_id is None:
        raise RuntimeError(f"Tool route {step.route!r} has no call id.")
    return AgentInput(
        model=step.model,
        previous_response_id=step.response_id,
        tool_call_id=step.call_id,
        tool_output=json.dumps({"result": result}, separators=(",", ":")),
        model_steps=step.model_steps,
    )


def _operands(step: ModelStep) -> BinaryOperands:
    if step.arguments is None:
        raise RuntimeError(f"Tool route {step.route!r} has no arguments.")
    return BinaryOperands.model_validate_json(step.arguments)


@task
async def add(step: ModelStep) -> AgentInput:
    operands = _operands(step)
    return _tool_continuation(step, operands.left + operands.right)


@task
async def multiply(step: ModelStep) -> AgentInput:
    operands = _operands(step)
    return _tool_continuation(step, operands.left * operands.right)


@task
async def finish(step: ModelStep) -> AgentReply:
    if step.answer is None:
        raise RuntimeError("The answer route has no text.")
    return AgentReply(text=step.answer, response_id=step.response_id)


workflow = Workflow(
    "openai_tool_loop",
    policy=WorkflowPolicy(allow_cycles=True),
    start=Node(run=begin_turn, next="reason"),
    reason=Node(
        run=reason,
        route_on=ModelStep.route,
        next={
            "add": "add",
            "multiply": "multiply",
            "answer": "result",
        },
    ),
    add=Node(run=add, next="reason"),
    multiply=Node(run=multiply, next="reason"),
    result=finish,
)


async def run_cli(message: str | None, model: str) -> None:
    if "OPENAI_API_KEY" not in os.environ:
        typer.echo("Set OPENAI_API_KEY before running this prototype.", err=True)
        raise typer.Exit(code=2)

    supplied_message = "" if message is None else message.strip()
    if supplied_message:
        run = await workflow.run(message=supplied_message, model=model)
        typer.echo(run.result.text)
        return

    previous_response_id: str | None = None
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

        run = await workflow.run(
            message=user_message,
            model=model,
            previous_response_id=previous_response_id,
        )
        reply = run.result
        if not isinstance(reply, AgentReply):
            raise RuntimeError("The workflow did not produce an AgentReply.")
        typer.echo(f"agent> {reply.text}")
        previous_response_id = reply.response_id


@app.command()
def main(
    message: str | None = typer.Argument(
        None,
        help="One user message. Omit it to start the interactive loop.",
    ),
    model: str = typer.Option(
        os.environ.get("OPENAI_MODEL", DEFAULT_MODEL),
        help="OpenAI model used for every model step.",
    ),
) -> None:
    """Run the OpenAI tool-call loop."""
    asyncio.run(run_cli(message, model))


if __name__ == "__main__":
    app()
