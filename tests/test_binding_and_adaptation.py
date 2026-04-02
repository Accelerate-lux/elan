import pytest

from elan import Node, Workflow


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
