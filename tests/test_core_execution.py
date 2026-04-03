import pytest

from elan import Node, Workflow


@pytest.mark.asyncio
async def test_run_workflow_one_async_task(mock_task_factory, branch_id):
    async def _hello():
        return "Hello, world!"

    hello = mock_task_factory(_hello)

    workflow = Workflow("hello_world", start=hello)

    run = await workflow.run()

    hello.mock.assert_called_once_with()
    assert run.result == "Hello, world!"
    assert run.outputs == {
        branch_id[0]: {
            "_hello": ["Hello, world!"],
        }
    }


@pytest.mark.asyncio
async def test_run_workflow_one_sync_task(mock_task_factory, branch_id):
    def _hello():
        return "Hello, world!"

    hello = mock_task_factory(_hello)

    workflow = Workflow("hello_world", start=hello)

    run = await workflow.run()

    hello.mock.assert_called_once_with()
    assert run.result == "Hello, world!"
    assert run.outputs == {
        branch_id[0]: {
            "_hello": ["Hello, world!"],
        }
    }


@pytest.mark.asyncio
async def test_run_workflow_two_tasks(mock_task_factory, branch_id):
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
    assert run.result == "Hello, world!"
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": ["world"],
            "_greet": ["Hello, world!"],
        }
    }


@pytest.mark.asyncio
async def test_run_workflow_reserved_result_exports_value(mock_task_factory, branch_id):
    def _prepare():
        return 2, 3

    def _add(left: int, right: int):
        return left + right

    prepare = mock_task_factory(_prepare)
    add = mock_task_factory(_add)

    workflow = Workflow(
        "sum_ab",
        start=Node(run=prepare, next="result"),
        result=Node(run=add),
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    add.mock.assert_called_once_with(2, 3)
    assert run.result == 5
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": [(2, 3)],
            "_add": [5],
        }
    }

