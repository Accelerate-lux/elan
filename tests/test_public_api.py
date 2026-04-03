import pytest
from pydantic import BaseModel

from elan import Context, Input, Node, Upstream, Workflow, ref


@pytest.mark.asyncio
async def test_single_task_workflow(mock_task_factory, branch_id):
    async def _hello():
        return "Hello, world!"

    hello = mock_task_factory(_hello)

    run = await Workflow("hello_world", start=hello).run()

    hello.mock.assert_called_once_with()
    assert run.result == "Hello, world!"
    assert run.outputs == {
        branch_id[0]: {
            "_hello": ["Hello, world!"],
        }
    }


@pytest.mark.asyncio
async def test_literal_input_mapping(mock_task_factory, branch_id):
    def _prepare():
        return "world"

    async def _greet(name: str, title: str, punctuation: str):
        return f"Hello, {title} {name}{punctuation}"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    run = await Workflow(
        "greet_world",
        start=Node(run=prepare, bind_output="name", next="greet"),
        greet=Node(
            run=greet,
            bind_input={
                "title": "Dr",
                "punctuation": "!",
            },
        ),
    ).run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with(
        name="world",
        title="Dr",
        punctuation="!",
    )
    assert run.result == "Hello, Dr world!"
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": ["world"],
            "_greet": ["Hello, Dr world!"],
        }
    }


class GreetingContext(BaseModel):
    punctuation: str = "!"


@ref
class GreetingRefPayload(BaseModel):
    name: str


@pytest.mark.asyncio
async def test_ref_backed_binding(mock_task_factory, branch_id):
    def _prepare() -> GreetingRefPayload:
        return GreetingRefPayload(name="world")

    async def _greet(name: str, title: str, punctuation: str):
        return f"Hello, {title} {name}{punctuation}"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    run = await Workflow(
        "greet_world",
        context=GreetingContext,
        start=Node(run=prepare, next="greet"),
        greet=Node(
            run=greet,
            bind_input={
                "name": Upstream.name,
                "title": Input.title,
                "punctuation": Context.punctuation,
            },
        ),
    ).run(title="Dr")

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with(
        name="world",
        title="Dr",
        punctuation="!",
    )
    assert run.result == "Hello, Dr world!"
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": [GreetingRefPayload(name="world")],
            "_greet": ["Hello, Dr world!"],
        }
    }


@pytest.mark.asyncio
async def test_exclusive_branching_with_reserved_result(mock_task_factory, branch_id):
    def _prepare():
        return "world", "formal"

    async def _greet_formal(name: str):
        return f"Hello, {name}."

    async def _greet_casual(name: str):
        return f"Hey {name}!"

    def _identity(value: str):
        return value

    prepare = mock_task_factory(_prepare)
    greet_formal = mock_task_factory(_greet_formal)
    greet_casual = mock_task_factory(_greet_casual)
    identity = mock_task_factory(_identity)

    run = await Workflow(
        "branching_greet",
        start=Node(
            run=prepare,
            bind_output=["name", "style"],
            route_on="style",
            next={
                "formal": "greet_formal",
                "casual": "greet_casual",
            },
        ),
        greet_formal=Node(run=greet_formal, next="result"),
        greet_casual=Node(run=greet_casual, next="result"),
        result=Node(run=identity),
    ).run()

    prepare.mock.assert_called_once_with()
    greet_formal.mock.assert_called_once_with(name="world")
    greet_casual.mock.assert_not_called()
    identity.mock.assert_called_once_with("Hello, world.")
    assert run.result == "Hello, world."
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": [("world", "formal")],
            "_greet_formal": ["Hello, world."],
            "_identity": ["Hello, world."],
        }
    }


@pytest.mark.asyncio
async def test_fan_out_without_reserved_result(mock_task_factory, branch_id):
    def _prepare():
        return "world"

    async def _greet(name: str):
        return f"Hello, {name}!"

    async def _badge(name: str):
        return f"badge:{name}"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)
    badge = mock_task_factory(_badge)

    run = await Workflow(
        "fan_out_profile",
        start=Node(
            run=prepare,
            bind_output="name",
            next=["greet", "badge"],
        ),
        greet=greet,
        badge=badge,
    ).run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with(name="world")
    badge.mock.assert_called_once_with(name="world")
    assert run.result is None
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": ["world"],
        },
        branch_id[1]: {
            "_greet": ["Hello, world!"],
        },
        branch_id[2]: {
            "_badge": ["badge:world"],
        },
    }


@pytest.mark.asyncio
async def test_registry_resolution_with_reserved_result(mock_task_factory, branch_id):
    def _prepare():
        return 2, 3

    def _add(left: int, right: int):
        return left + right

    prepare = mock_task_factory(_prepare, alias="prepare")
    add = mock_task_factory(_add, alias="add")

    run = await Workflow(
        "sum_ab",
        start=Node(run="prepare", next="result"),
        result="add",
    ).run()

    prepare.mock.assert_called_once_with()
    add.mock.assert_called_once_with(2, 3)
    assert run.result == 5
    assert run.outputs == {
        branch_id[0]: {
            "prepare": [(2, 3)],
            "add": [5],
        }
    }

