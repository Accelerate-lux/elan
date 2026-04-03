import pytest

from elan import Node, Workflow


@pytest.mark.asyncio
async def test_run_workflow_exclusive_branch_from_named_payload(mock_task_factory, branch_id):
    def _prepare():
        return "world", "formal"

    async def _greet_formal(name: str):
        return f"Hello, {name}."

    async def _greet_casual(name: str):
        return f"Hey {name}!"

    prepare = mock_task_factory(_prepare)
    greet_formal = mock_task_factory(_greet_formal)
    greet_casual = mock_task_factory(_greet_casual)

    workflow = Workflow(
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
        greet_formal=greet_formal,
        greet_casual=greet_casual,
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet_formal.mock.assert_called_once_with(name="world")
    greet_casual.mock.assert_not_called()
    assert run.result is None
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": [("world", "formal")],
            "_greet_formal": ["Hello, world."],
        }
    }


@pytest.mark.asyncio
async def test_run_workflow_exclusive_branch_from_raw_dict(mock_task_factory, branch_id):
    def _prepare():
        return {"style": "formal", "name": "world"}

    async def _greet_formal(payload: dict[str, str]):
        return f"Hello, {payload['name']}."

    async def _greet_casual(payload: dict[str, str]):
        return f"Hey {payload['name']}!"

    prepare = mock_task_factory(_prepare)
    greet_formal = mock_task_factory(_greet_formal)
    greet_casual = mock_task_factory(_greet_casual)

    workflow = Workflow(
        "branching_greet",
        start=Node(
            run=prepare,
            route_on="style",
            next={
                "formal": "greet_formal",
                "casual": "greet_casual",
            },
        ),
        greet_formal=greet_formal,
        greet_casual=greet_casual,
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet_formal.mock.assert_called_once_with({"style": "formal", "name": "world"})
    greet_casual.mock.assert_not_called()
    assert run.result is None
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": [{"style": "formal", "name": "world"}],
            "_greet_formal": ["Hello, world."],
        }
    }


@pytest.mark.asyncio
async def test_run_workflow_missing_route_on_fails_clearly(mock_task_factory):
    def _prepare():
        return "world", "formal"

    async def _greet_formal(name: str):
        return f"Hello, {name}."

    prepare = mock_task_factory(_prepare)
    greet_formal = mock_task_factory(_greet_formal)

    workflow = Workflow(
        "branching_greet",
        start=Node(
            run=prepare,
            bind_output=["name", "style"],
            next={"formal": "greet_formal"},
        ),
        greet_formal=greet_formal,
    )

    with pytest.raises(TypeError, match="route_on"):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_route_on_missing_field_fails_clearly(mock_task_factory):
    def _prepare():
        return "world"

    async def _greet_formal(name: str):
        return f"Hello, {name}."

    prepare = mock_task_factory(_prepare)
    greet_formal = mock_task_factory(_greet_formal)

    workflow = Workflow(
        "branching_greet",
        start=Node(
            run=prepare,
            bind_output="name",
            route_on="style",
            next={"formal": "greet_formal"},
        ),
        greet_formal=greet_formal,
    )

    with pytest.raises(TypeError, match="does not provide field 'style'"):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_route_on_unmapped_value_fails_clearly(mock_task_factory):
    def _prepare():
        return "world", "unknown"

    async def _greet_formal(name: str):
        return f"Hello, {name}."

    prepare = mock_task_factory(_prepare)
    greet_formal = mock_task_factory(_greet_formal)

    workflow = Workflow(
        "branching_greet",
        start=Node(
            run=prepare,
            bind_output=["name", "style"],
            route_on="style",
            next={"formal": "greet_formal"},
        ),
        greet_formal=greet_formal,
    )

    with pytest.raises(KeyError, match="does not define a route for value 'unknown'"):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_branch_mapping_unknown_node_fails_clearly(mock_task_factory):
    def _prepare():
        return "world", "formal"

    prepare = mock_task_factory(_prepare)

    workflow = Workflow(
        "branching_greet",
        start=Node(
            run=prepare,
            bind_output=["name", "style"],
            route_on="style",
            next={"formal": "missing"},
        ),
    )

    with pytest.raises(KeyError, match="references unknown node 'missing'"):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_fan_out_duplicates_payload(mock_task_factory, branch_id):
    def _prepare():
        return "world"

    async def _greet(name: str):
        return f"Hello, {name}!"

    async def _badge(name: str):
        return f"badge:{name}"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)
    badge = mock_task_factory(_badge)

    workflow = Workflow(
        "fan_out_profile",
        start=Node(
            run=prepare,
            bind_output="name",
            next=["greet", "badge"],
        ),
        greet=greet,
        badge=badge,
    )

    run = await workflow.run()

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
async def test_run_workflow_fan_out_with_reserved_result_is_invalid(mock_task_factory):
    def _prepare():
        return "world"

    async def _greet(name: str):
        return f"Hello, {name}!"

    def _identity(value: str):
        return value

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)
    identity = mock_task_factory(_identity)

    workflow = Workflow(
        "fan_out_profile",
        start=Node(
            run=prepare,
            bind_output="name",
            next=["greet"],
        ),
        greet=Node(run=greet, next="result"),
        result=Node(run=identity),
    )

    with pytest.raises(NotImplementedError, match="Fan-out with reserved result"):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_branch_ids_are_distinct_for_siblings(mock_task_factory, branch_id):
    def _prepare():
        return "world"

    async def _first(name: str):
        return f"first:{name}"

    async def _second(name: str):
        return f"second:{name}"

    prepare = mock_task_factory(_prepare)
    first = mock_task_factory(_first)
    second = mock_task_factory(_second)

    workflow = Workflow(
        "fan_out_profile",
        start=Node(
            run=prepare,
            bind_output="name",
            next=["first", "second"],
        ),
        first=first,
        second=second,
    )

    run = await workflow.run()

    assert sorted(run.outputs) == [branch_id[0], branch_id[1], branch_id[2]]
    assert run.outputs[branch_id[1]] != run.outputs[branch_id[2]]

