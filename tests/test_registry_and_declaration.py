import pytest

from elan import Node, Workflow, task


@pytest.mark.asyncio
async def test_run_workflow_start_resolved_by_canonical_key(mock_task_factory):
    async def _hello():
        return "Hello, world!"

    hello = mock_task_factory(_hello)

    workflow = Workflow("hello_world", start=hello.key)

    run = await workflow.run()

    hello.mock.assert_called_once_with()
    assert run.result == "Hello, world!"
    assert run.outputs == {"_hello": ["Hello, world!"]}


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
    assert run.result == "Hello, world!"
    assert run.outputs == {
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
    assert run.result == "Hello, world!"
    assert run.outputs == {
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
