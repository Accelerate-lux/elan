import pytest

from elan import Node, Workflow


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
        start=Node(run=prepare, output=["name"], next="greet"),
        greet=greet,
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with(name="world")
    assert run.result == {
        "_prepare": ["world"],
        "_greet": ["Hello, world!"],
    }
