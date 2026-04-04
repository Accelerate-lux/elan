import asyncio

import pytest

from elan import Join, Node, When, Workflow, task


@pytest.mark.asyncio
async def test_run_workflow_join_one_contribution_returns_one_item_list(
    mock_task_factory,
    branch_id,
):
    def _prepare():
        return 2, 3

    prepare = mock_task_factory(_prepare)

    run = await Workflow(
        "sum_ab",
        start=Node(run=prepare, next="result"),
        result=Join(),
    ).run()

    prepare.mock.assert_called_once_with()
    assert run.result == [(2, 3)]
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": [(2, 3)],
        }
    }


@pytest.mark.asyncio
async def test_run_workflow_join_multiple_contributions_follow_arrival_order(
    mock_task_factory,
    branch_id,
):
    def _prepare():
        return "world"

    async def _greet(name: str):
        await asyncio.sleep(0)
        return f"Hello, {name}!"

    async def _badge(name: str):
        await asyncio.sleep(0.01)
        return f"badge:{name}"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)
    badge = mock_task_factory(_badge)

    run = await Workflow(
        "fan_out_profile",
        start=Node(
            run=prepare,
            bind_output="name",
            next=["greet", "badge"],
        ),
        greet=Node(run=greet, next="result"),
        badge=Node(run=badge, next="result"),
        result=Join(),
    ).run()

    greet.mock.assert_called_once_with(name="world")
    badge.mock.assert_called_once_with(name="world")
    assert run.result == ["Hello, world!", "badge:world"]
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
async def test_run_workflow_join_reducer_receives_collected_list(
    mock_task_factory,
    branch_id,
):
    def _prepare():
        return "world"

    async def _greet(name: str):
        await asyncio.sleep(0)
        return f"Hello, {name}!"

    async def _badge(name: str):
        await asyncio.sleep(0.01)
        return f"badge:{name}"

    def _collect(values: list[str]):
        return " | ".join(values)

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)
    badge = mock_task_factory(_badge)
    collect = mock_task_factory(_collect)

    run = await Workflow(
        "fan_out_profile",
        start=Node(
            run=prepare,
            bind_output="name",
            next=["greet", "badge"],
        ),
        greet=Node(run=greet, next="result"),
        badge=Node(run=badge, next="result"),
        result=Join(run=collect),
    ).run()

    collect.mock.assert_called_once_with(["Hello, world!", "badge:world"])
    assert run.result == "Hello, world! | badge:world"
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
async def test_run_workflow_join_reducer_receives_empty_list_for_zero_contributions(
    mock_task_factory,
    branch_id,
):
    def _prepare():
        return "world"

    async def _audit(name: str):
        return f"audit:{name}"

    def _count(values: list[str]):
        return len(values)

    prepare = mock_task_factory(_prepare)
    audit = mock_task_factory(_audit)
    count = mock_task_factory(_count)

    run = await Workflow(
        "fan_out_profile",
        start=Node(
            run=prepare,
            bind_output="name",
            next=["audit"],
        ),
        audit=audit,
        result=Join(run=count),
    ).run()

    audit.mock.assert_called_once_with(name="world")
    count.mock.assert_called_once_with([])
    assert run.result == 0
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": ["world"],
        },
        branch_id[1]: {
            "_audit": ["audit:world"],
        },
    }


@pytest.mark.asyncio
async def test_run_workflow_join_excludes_non_contributing_branches(
    mock_task_factory,
    branch_id,
):
    def _prepare():
        return "world"

    async def _greet(name: str):
        return f"Hello, {name}!"

    async def _audit(name: str):
        return f"audit:{name}"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)
    audit = mock_task_factory(_audit)

    run = await Workflow(
        "fan_out_profile",
        start=Node(
            run=prepare,
            bind_output="name",
            next=["greet", "audit"],
        ),
        greet=Node(run=greet, next="result"),
        audit=audit,
        result=Join(),
    ).run()

    greet.mock.assert_called_once_with(name="world")
    audit.mock.assert_called_once_with(name="world")
    assert run.result == ["Hello, world!"]
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": ["world"],
        },
        branch_id[1]: {
            "_greet": ["Hello, world!"],
        },
        branch_id[2]: {
            "_audit": ["audit:world"],
        },
    }


@pytest.mark.asyncio
async def test_run_workflow_join_with_mixed_target_producer_list(
    mock_task_factory,
    branch_id,
):
    def _prepare():
        return "world", True

    async def _greet(name: str):
        await asyncio.sleep(0)
        return f"Hello, {name}!"

    async def _badge(name: str):
        await asyncio.sleep(0.01)
        return f"badge:{name}"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)
    badge = mock_task_factory(_badge)

    run = await Workflow(
        "conditional_routes",
        start=Node(
            run=prepare,
            bind_output=["name", "should_badge"],
            next=["greet", When("should_badge", "badge")],
        ),
        greet=Node(run=greet, next="result"),
        badge=Node(run=badge, next="result"),
        result=Join(),
    ).run()

    greet.mock.assert_called_once_with(name="world")
    badge.mock.assert_called_once_with(name="world")
    assert run.result == ["Hello, world!", "badge:world"]
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": [("world", True)],
        },
        branch_id[1]: {
            "_greet": ["Hello, world!"],
        },
        branch_id[2]: {
            "_badge": ["badge:world"],
        },
    }


@pytest.mark.asyncio
async def test_run_workflow_exclusive_branch_can_route_to_join(
    mock_task_factory,
    branch_id,
):
    def _prepare():
        return "world", "formal"

    async def _greet_formal(name: str):
        return f"Hello, {name}."

    async def _greet_casual(name: str):
        return f"Hey {name}!"

    prepare = mock_task_factory(_prepare)
    greet_formal = mock_task_factory(_greet_formal)
    greet_casual = mock_task_factory(_greet_casual)

    run = await Workflow(
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
        greet_formal=Node(run=greet_formal, next="result"),
        greet_casual=Node(run=greet_casual, next="result"),
        result=Join(),
    ).run()

    greet_formal.mock.assert_called_once_with(name="world")
    greet_casual.mock.assert_not_called()
    assert run.result == ["Hello, world."]
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": [("world", "formal")],
            "_greet_formal": ["Hello, world."],
        }
    }


def test_join_outside_reserved_result_fails_clearly():
    @task
    def hello():
        return "Hello, world!"

    with pytest.raises(TypeError, match="only allows Join"):
        Workflow(
            "invalid_join",
            start=hello,
            collect=Join(),
        )
