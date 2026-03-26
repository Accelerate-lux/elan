import pytest

from elan import Workflow


@pytest.mark.asyncio
async def test_run_workflow_one_async_task(mock_task_factory):
    async def _hello():
        return "Hello, world!"

    hello = mock_task_factory(_hello)

    workflow = Workflow("hello_world", start=hello)

    result = await workflow.run()

    hello.mock.assert_called_once_with()
    assert result == "Hello, world!"


@pytest.mark.asyncio
async def test_run_workflow_one_sync_task(mock_task_factory):
    def _hello():
        return "Hello, world!"

    hello = mock_task_factory(_hello)

    workflow = Workflow("hello_world", start=hello)

    result = await workflow.run()

    hello.mock.assert_called_once_with()
    assert result == "Hello, world!"
