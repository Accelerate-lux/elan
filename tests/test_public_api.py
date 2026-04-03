import pytest
from pydantic import BaseModel

from elan import Context, Input, Node, Upstream, Workflow, ref


@pytest.mark.asyncio
async def test_single_task_workflow(mock_task_factory):
    async def _hello():
        return "Hello, world!"

    hello = mock_task_factory(_hello)

    run = await Workflow("hello_world", start=hello).run()

    hello.mock.assert_called_once_with()
    assert run.result == "Hello, world!"
    assert run.outputs == {"_hello": ["Hello, world!"]}


@pytest.mark.asyncio
async def test_literal_input_mapping(mock_task_factory):
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
        "_prepare": ["world"],
        "_greet": ["Hello, Dr world!"],
    }


class GreetingContext(BaseModel):
    punctuation: str = "!"


@ref
class GreetingRefPayload(BaseModel):
    name: str


@pytest.mark.asyncio
async def test_ref_backed_binding(mock_task_factory):
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
        "_prepare": [GreetingRefPayload(name="world")],
        "_greet": ["Hello, Dr world!"],
    }


@pytest.mark.asyncio
async def test_registry_resolution_with_reserved_result(mock_task_factory):
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
        "prepare": [(2, 3)],
        "add": [5],
    }
