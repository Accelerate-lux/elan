import pytest
from pydantic import BaseModel

from elan import Binder, Context, Input, Join, Node, Upstream, Workflow, ref, task


@pytest.mark.asyncio
async def test_parent_node_runs_child_workflow_and_receives_result(branch_id):
    @task
    def prepare():
        return 2

    @task
    def double(value: int) -> int:
        return value * 2

    child = Workflow("double_value", start=double)

    run = await Workflow(
        "parent",
        start=Node(run=prepare, next="child"),
        child=Node(run=child),
    ).run()

    assert run.result == 4
    assert run.outputs == {
        branch_id[0]: {
            "prepare": [2],
            "double_value": [4],
        }
    }


@pytest.mark.asyncio
async def test_child_workflow_can_consume_raw_dict_packet(branch_id):
    @task
    def prepare():
        return {"name": "world"}

    @task
    def consume(payload: dict[str, str]) -> str:
        return payload["name"]

    child = Workflow("consume_payload", start=consume)

    run = await Workflow(
        "parent",
        start=Node(run=prepare, next="child"),
        child=Node(run=child),
    ).run()

    assert run.result == "world"
    assert run.outputs == {
        branch_id[0]: {
            "prepare": [{"name": "world"}],
            "consume_payload": ["world"],
        }
    }


@ref
class ChildPayload(BaseModel):
    name: str


@pytest.mark.asyncio
async def test_child_workflow_can_consume_pydantic_packet(branch_id):
    @task
    def prepare() -> ChildPayload:
        return ChildPayload(name="world")

    @task
    def consume(payload: ChildPayload) -> str:
        return payload.name

    child = Workflow("consume_model", start=consume)

    run = await Workflow(
        "parent",
        start=Node(run=prepare, next="child"),
        child=Node(run=child),
    ).run()

    assert run.result == "world"
    assert run.outputs == {
        branch_id[0]: {
            "prepare": [ChildPayload(name="world")],
            "consume_model": ["world"],
        }
    }


@pytest.mark.asyncio
async def test_parent_bind_input_adapts_child_workflow_input(branch_id):
    @task
    def prepare():
        return "Ada", "Lovelace"

    @task
    def greet(name: str) -> str:
        return f"Hello, {name}"

    child = Workflow("greet_name", start=greet)

    run = await Workflow(
        "parent",
        start=Node(run=prepare, bind_output=["first", "last"], next="child"),
        child=Node(
            run=child,
            bind_input={"name": Upstream.first},
        ),
    ).run()

    assert run.result == "Hello, Ada"
    assert run.outputs == {
        branch_id[0]: {
            "prepare": [("Ada", "Lovelace")],
            "greet_name": ["Hello, Ada"],
        }
    }


@pytest.mark.asyncio
async def test_child_workflow_with_join_returns_reduced_result(branch_id):
    @task
    def prepare():
        return 3

    @task
    def identity(value: int) -> int:
        return value

    @task
    def plus_one(value: int) -> int:
        return value + 1

    @task
    def plus_two(value: int) -> int:
        return value + 2

    @task
    def total(values: list[int]) -> int:
        return sum(values)

    child = Workflow(
        "sum_offsets",
        start=Node(run=identity, next=["plus_one", "plus_two"]),
        plus_one=Node(run=plus_one, next="result"),
        plus_two=Node(run=plus_two, next="result"),
        result=Join(run=total),
    )

    run = await Workflow(
        "parent",
        start=Node(run=prepare, next="child"),
        child=Node(run=child),
    ).run()

    assert run.result == 9
    assert run.outputs == {
        branch_id[0]: {
            "prepare": [3],
            "sum_offsets": [9],
        }
    }


@pytest.mark.asyncio
async def test_yielded_items_can_run_child_workflows_and_join_in_parent(branch_id):
    @task
    def produce():
        yield 1
        yield 2

    @task
    def double(value: int) -> int:
        return value * 2

    @task
    def total(values: list[int]) -> int:
        return sum(values)

    child = Workflow("double_value", start=double)

    run = await Workflow(
        "parent",
        start=Node(run=produce, next="child"),
        child=Node(run=child, next="result"),
        result=Join(run=total),
    ).run()

    assert run.result == 6
    assert run.outputs[branch_id[0]] == {"produce": [[1, 2]]}
    child_outputs = [
        outputs["double_value"][0]
        for branch, outputs in run.outputs.items()
        if branch != branch_id[0]
    ]
    assert sorted(child_outputs) == [2, 4]


class RunContext(BaseModel):
    prefix: str = "draft"


@pytest.mark.asyncio
async def test_child_workflow_inherits_parent_context(branch_id):
    @task
    def prepare():
        return "post"

    @task
    def label(value: str, prefix: str) -> str:
        return f"{prefix}:{value}"

    child = Workflow(
        "label_value",
        context=RunContext,
        start=Node(
            run=label,
            bind_input=Binder[label](
                prefix=Context.prefix,
            ),
        ),
    )

    run = await Workflow(
        "parent",
        context=RunContext,
        start=Node(
            run=prepare,
            context=Binder[RunContext](prefix="published"),
            next="child",
        ),
        child=Node(run=child),
    ).run()

    assert run.result == "published:post"
    assert run.outputs == {
        branch_id[0]: {
            "prepare": ["post"],
            "label_value": ["published:post"],
        }
    }


@pytest.mark.asyncio
async def test_child_workflow_rejects_incompatible_inherited_context():
    class OtherContext(BaseModel):
        prefix: str = "other"

    @task
    def prepare():
        return "post"

    @task
    def label(value: str) -> str:
        return value

    child = Workflow("child", context=OtherContext, start=label)
    parent = Workflow(
        "parent",
        context=RunContext,
        start=Node(run=prepare, next="child"),
        child=Node(run=child),
    )

    with pytest.raises(
        TypeError,
        match="cannot inherit context 'RunContext' as 'OtherContext'",
    ):
        await parent.run()
