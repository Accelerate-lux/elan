import pytest
from pydantic import BaseModel

from elan import Node, Workflow, task


@pytest.mark.asyncio
async def test_run_workflow_one_async_task(mock_task_factory):
    async def _hello():
        return "Hello, world!"

    hello = mock_task_factory(_hello)

    workflow = Workflow("hello_world", start=hello)

    run = await workflow.run()

    hello.mock.assert_called_once_with()
    assert run.result == {"_hello": ["Hello, world!"]}


@pytest.mark.asyncio
async def test_run_workflow_one_sync_task(mock_task_factory):
    def _hello():
        return "Hello, world!"

    hello = mock_task_factory(_hello)

    workflow = Workflow("hello_world", start=hello)

    run = await workflow.run()

    hello.mock.assert_called_once_with()
    assert run.result == {"_hello": ["Hello, world!"]}


@pytest.mark.asyncio
async def test_run_workflow_two_tasks(mock_task_factory):
    def _prepare():
        return "world"

    async def _greet(name):
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
    greet.mock.assert_called_once_with("world")
    assert run.result == {
        "_prepare": ["world"],
        "_greet": ["Hello, world!"],
    }


@pytest.mark.asyncio
async def test_run_workflow_two_tasks_mapped_output(mock_task_factory):
    def _prepare():
        return "world"

    async def _greet(name):
        return f"Hello, {name}!"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, output="name", next="greet"),
        greet=greet,
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with(name="world")
    assert run.result == {
        "_prepare": ["world"],
        "_greet": ["Hello, world!"],
    }


@pytest.mark.asyncio
async def test_run_workflow_two_tasks_discard_output(mock_task_factory):
    def _prepare():
        return "ignored", "world"

    async def _greet(name):
        return f"Hello, {name}!"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, output=[..., "name"], next="greet"),
        greet=greet,
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with(name="world")
    assert run.result == {
        "_prepare": [("ignored", "world")],
        "_greet": ["Hello, world!"],
    }


@pytest.mark.asyncio
async def test_run_workflow_tuple_output(mock_task_factory):
    def _prepare():
        return "hello", "world"

    async def _greet(prefix: str, name: str):
        return f"{prefix.title()}, {name}!"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, next="greet"),
        greet=greet,
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with("hello", "world")
    assert run.result == {
        "_prepare": [("hello", "world")],
        "_greet": ["Hello, world!"],
    }


@pytest.mark.asyncio
async def test_run_workflow_tuple_output_arity_mismatch(mock_task_factory):
    def _prepare():
        return "hello", "world"

    async def _greet(name: str):
        return f"Hello, {name}!"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, next="greet"),
        greet=greet,
    )

    with pytest.raises(TypeError, match="tuple output of length 2"):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_tuple_output_type_mismatch(mock_task_factory):
    def _prepare():
        return ("world",)

    async def _greet(count: int):
        return f"Hello x{count}"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, next="greet"),
        greet=greet,
    )

    with pytest.raises(TypeError, match="parameter 'count'"):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_list_output_is_opaque(mock_task_factory):
    def _prepare():
        return ["hello", "world"]

    async def _greet(values: list[str]):
        return f"{values[0].title()}, {values[1]}!"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, next="greet"),
        greet=greet,
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with(["hello", "world"])
    assert run.result == {
        "_prepare": [["hello", "world"]],
        "_greet": ["Hello, world!"],
    }


@pytest.mark.asyncio
async def test_run_workflow_raw_dict_output_is_opaque(mock_task_factory):
    def _prepare():
        return {"name": "world"}

    async def _greet(payload: dict[str, str]):
        return f"Hello, {payload['name']}!"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, next="greet"),
        greet=greet,
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with({"name": "world"})
    assert run.result == {
        "_prepare": [{"name": "world"}],
        "_greet": ["Hello, world!"],
    }


@pytest.mark.asyncio
async def test_run_workflow_raw_dict_output_does_not_unpack(mock_task_factory):
    def _prepare():
        return {"name": "world"}

    async def _greet(name: str):
        return f"Hello, {name}!"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, next="greet"),
        greet=greet,
    )

    with pytest.raises(TypeError, match="annotation <class 'str'>"):
        await workflow.run()


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


@pytest.mark.asyncio
async def test_run_workflow_start_resolved_by_canonical_key(mock_task_factory):
    async def _hello():
        return "Hello, world!"

    hello = mock_task_factory(_hello)

    workflow = Workflow("hello_world", start=hello.key)

    run = await workflow.run()

    hello.mock.assert_called_once_with()
    assert run.result == {"_hello": ["Hello, world!"]}


@pytest.mark.asyncio
async def test_run_workflow_node_resolved_by_canonical_key(mock_task_factory):
    def _prepare():
        return "world"

    async def _greet(name):
        return f"Hello, {name}!"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare.key, output="name", next="greet"),
        greet=greet.key,
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with(name="world")
    assert run.result == {
        "_prepare": ["world"],
        "_greet": ["Hello, world!"],
    }


@pytest.mark.asyncio
async def test_run_workflow_resolves_tasks_by_alias(mock_task_factory):
    def _prepare():
        return "world"

    async def _greet(name):
        return f"Hello, {name}!"

    prepare = mock_task_factory(_prepare, alias="prepare")
    greet = mock_task_factory(_greet, alias="greet")

    workflow = Workflow(
        "greet_world",
        start=Node(run="prepare", output="name", next="greet_node"),
        greet_node="greet",
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with(name="world")
    assert run.result == {
        "prepare": ["world"],
        "greet": ["Hello, world!"],
    }


def test_duplicate_task_alias_fails():
    @task(alias="duplicate")
    def first():
        return "first"

    with pytest.raises(
        ValueError, match="Task alias 'duplicate' is already registered"
    ):

        @task(alias="duplicate")
        def second():
            return "second"

    assert first.alias == "duplicate"


@pytest.mark.asyncio
async def test_unknown_task_reference_fails_clearly():
    workflow = Workflow("hello_world", start="missing.task")

    with pytest.raises(KeyError, match="Unknown task 'missing.task'"):
        await workflow.run()


@pytest.mark.asyncio
async def test_raw_callable_is_rejected():
    async def _hello():
        return "Hello, world!"

    workflow = Workflow("hello_world", start=_hello)

    with pytest.raises(TypeError, match="expects tasks decorated with @task"):
        await workflow.run()
