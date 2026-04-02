import pytest
from pydantic import BaseModel

from elan import Node, Workflow


class UserPayload(BaseModel):
    name: str
    age: int


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
async def test_linear_workflow(mock_task_factory):
    def _prepare():
        return "world"

    async def _greet(name: str):
        return f"Hello, {name}!"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    run = await Workflow(
        "greet_world",
        start=Node(run=prepare, next="greet"),
        greet=greet,
    ).run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with("world")
    assert run.result == "Hello, world!"
    assert run.outputs == {
        "_prepare": ["world"],
        "_greet": ["Hello, world!"],
    }


@pytest.mark.asyncio
async def test_output_mapping(mock_task_factory):
    def _prepare():
        return "world"

    async def _greet(name: str):
        return f"Hello, {name}!"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    run = await Workflow(
        "greet_world",
        start=Node(run=prepare, output="name", next="greet"),
        greet=greet,
    ).run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with(name="world")
    assert run.result == "Hello, world!"
    assert run.outputs == {
        "_prepare": ["world"],
        "_greet": ["Hello, world!"],
    }


@pytest.mark.asyncio
async def test_structured_payload_binding(mock_task_factory):
    def _prepare() -> UserPayload:
        return UserPayload(name="world", age=32)

    async def _greet(name: str):
        return f"Hello, {name}!"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    run = await Workflow(
        "greet_world",
        start=Node(run=prepare, next="greet"),
        greet=greet,
    ).run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with(name="world")
    assert run.result == "Hello, world!"
    assert run.outputs == {
        "_prepare": [UserPayload(name="world", age=32)],
        "_greet": ["Hello, world!"],
    }


@pytest.mark.asyncio
async def test_task_registry_resolution(mock_task_factory):
    def _prepare():
        return "world"

    async def _greet(name: str):
        return f"Hello, {name}!"

    prepare = mock_task_factory(_prepare, alias="prepare")
    greet = mock_task_factory(_greet, alias="greet")

    run = await Workflow(
        "greet_world",
        start=Node(run="prepare", output="name", next="greet_node"),
        greet_node="greet",
    ).run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with(name="world")
    assert run.result == "Hello, world!"
    assert run.outputs == {
        "prepare": ["world"],
        "greet": ["Hello, world!"],
    }


@pytest.mark.asyncio
async def test_reserved_result_node(mock_task_factory):
    def _prepare():
        return 2, 3

    def _add(left: int, right: int):
        return left + right

    prepare = mock_task_factory(_prepare)
    add = mock_task_factory(_add)

    run = await Workflow(
        "sum_ab",
        start=Node(run=prepare, next="result"),
        result=Node(run=add),
    ).run()

    prepare.mock.assert_called_once_with()
    add.mock.assert_called_once_with(2, 3)
    assert run.result == 5
    assert run.outputs == {
        "_prepare": [(2, 3)],
        "_add": [5],
    }
