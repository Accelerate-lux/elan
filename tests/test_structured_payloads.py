import pytest
from pydantic import BaseModel

from elan import Node, Workflow


class UserPayload(BaseModel):
    name: str
    age: int


class NameOnlyPayload(BaseModel):
    name: str


@pytest.mark.asyncio
async def test_run_workflow_pydantic_payload_auto_unpack(mock_task_factory):
    def _prepare() -> UserPayload:
        return UserPayload(name="world", age=32)

    async def _greet(name: str):
        return f"Hello, {name}!"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, next="greet"),
        greet=greet,
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with(name="world")
    assert run.result == {
        "_prepare": [UserPayload(name="world", age=32)],
        "_greet": ["Hello, world!"],
    }


@pytest.mark.asyncio
async def test_run_workflow_pydantic_payload_ignores_extra_fields(mock_task_factory):
    def _prepare() -> UserPayload:
        return UserPayload(name="world", age=32)

    async def _greet(name: str, **kwargs):
        return f"Hello, {name}!"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, next="greet"),
        greet=greet,
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with(name="world")
    assert run.result == {
        "_prepare": [UserPayload(name="world", age=32)],
        "_greet": ["Hello, world!"],
    }


@pytest.mark.asyncio
async def test_run_workflow_pydantic_payload_missing_required_field(mock_task_factory):
    def _prepare() -> NameOnlyPayload:
        return NameOnlyPayload(name="world")

    async def _greet(name: str, age: int):
        return f"Hello, {name}! ({age})"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, next="greet"),
        greet=greet,
    )

    with pytest.raises(TypeError, match="missing required inputs: age"):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_pydantic_payload_pass_through(mock_task_factory):
    def _prepare() -> UserPayload:
        return UserPayload(name="world", age=32)

    async def _greet(user: UserPayload):
        return f"Hello, {user.name}!"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, next="greet"),
        greet=greet,
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with(UserPayload(name="world", age=32))
    assert run.result == {
        "_prepare": [UserPayload(name="world", age=32)],
        "_greet": ["Hello, world!"],
    }
