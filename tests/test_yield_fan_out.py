import asyncio
from typing import Literal

import pytest
from pydantic import BaseModel

from elan import Join, Node, Workflow, ref, task


@pytest.mark.asyncio
async def test_sync_generator_yields_scalars_to_downstream_branches(branch_id):
    @task
    def produce_numbers():
        yield 1
        yield 2
        yield 3

    @task
    def double(value: int) -> int:
        return value * 2

    @task
    def collect(values: list[int]) -> list[int]:
        return sorted(values)

    run = await Workflow(
        "yield_numbers",
        start=Node(run=produce_numbers, next="double"),
        double=Node(run=double, next="result"),
        result=Join(run=collect),
    ).run()

    assert run.result == [2, 4, 6]
    assert run.outputs == {
        branch_id[0]: {
            "produce_numbers": [[1, 2, 3]],
        },
        branch_id[1]: {
            "double": [2],
        },
        branch_id[2]: {
            "double": [4],
        },
        branch_id[3]: {
            "double": [6],
        },
    }


@pytest.mark.asyncio
async def test_async_generator_schedules_downstream_before_generator_finishes():
    events: list[str] = []

    @task
    async def produce_numbers():
        events.append("yield-1")
        yield 1
        await asyncio.sleep(0.05)
        events.append("yield-2")
        yield 2

    @task
    async def consume(value: int) -> int:
        events.append(f"consume-{value}")
        return value

    @task
    def collect(values: list[int]) -> list[int]:
        return sorted(values)

    run = await Workflow(
        "stream_yield_numbers",
        start=Node(run=produce_numbers, next="consume"),
        consume=Node(run=consume, next="result"),
        result=Join(run=collect),
    ).run()

    assert run.result == [1, 2]
    assert events.index("consume-1") < events.index("yield-2")


@pytest.mark.asyncio
async def test_yielded_items_route_through_bind_output(branch_id):
    @task
    def produce_people():
        yield "Ada", "Lovelace"
        yield "Grace", "Hopper"

    @task
    def format_name(first: str, last: str) -> str:
        return f"{first} {last}"

    @task
    def collect(values: list[str]) -> list[str]:
        return sorted(values)

    run = await Workflow(
        "yield_people",
        start=Node(
            run=produce_people,
            bind_output=["first", "last"],
            next="format_name",
        ),
        format_name=Node(run=format_name, next="result"),
        result=Join(run=collect),
    ).run()

    assert run.result == ["Ada Lovelace", "Grace Hopper"]
    assert run.outputs[branch_id[0]] == {
        "produce_people": [[("Ada", "Lovelace"), ("Grace", "Hopper")]],
    }


@ref
class YieldRoutePayload(BaseModel):
    value: int
    route: Literal["small", "large"]


@pytest.mark.asyncio
async def test_yielded_items_route_through_route_on_mapping():
    @task
    def produce_routes():
        yield YieldRoutePayload(value=2, route="small")
        yield YieldRoutePayload(value=10, route="large")

    @task
    def small(value: int) -> str:
        return f"small:{value}"

    @task
    def large(value: int) -> str:
        return f"large:{value}"

    @task
    def collect(values: list[str]) -> list[str]:
        return sorted(values)

    run = await Workflow(
        "yield_routes",
        start=Node(
            run=produce_routes,
            route_on=YieldRoutePayload.route,
            next={
                "small": "small",
                "large": "large",
            },
        ),
        small=Node(run=small, next="result"),
        large=Node(run=large, next="result"),
        result=Join(run=collect),
    ).run()

    assert run.result == ["large:10", "small:2"]


@pytest.mark.asyncio
async def test_yielded_items_can_contribute_directly_to_join_result(branch_id):
    @task
    def produce_numbers():
        yield 3
        yield 4

    @task
    def collect(values: list[int]) -> int:
        return sum(values)

    run = await Workflow(
        "yield_direct_to_join",
        start=Node(run=produce_numbers, next="result"),
        result=Join(run=collect),
    ).run()

    assert run.result == 7
    assert run.outputs == {
        branch_id[0]: {
            "produce_numbers": [[3, 4]],
        },
    }


@pytest.mark.asyncio
async def test_zero_yielded_items_produce_empty_join_result(branch_id):
    @task
    def produce_nothing():
        if False:
            yield 1

    run = await Workflow(
        "yield_nothing",
        start=Node(run=produce_nothing, next="result"),
        result=Join(),
    ).run()

    assert run.result == []
    assert run.outputs == {
        branch_id[0]: {
            "produce_nothing": [[]],
        },
    }


@pytest.mark.asyncio
async def test_yielding_to_reserved_result_node_fails_clearly():
    @task
    def produce_numbers():
        yield 1

    @task
    def identity(value: int) -> int:
        return value

    workflow = Workflow(
        "yield_to_result_node",
        start=Node(run=produce_numbers, next="result"),
        result=Node(run=identity),
    )

    with pytest.raises(
        NotImplementedError,
        match="Yield-based branching with reserved result",
    ):
        await workflow.run()
