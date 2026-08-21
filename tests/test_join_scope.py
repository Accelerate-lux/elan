import asyncio

import pytest
from pydantic import BaseModel

from elan import Join, Node, Workflow, WorkflowPolicy, task


def _recorded_outputs(run, task_name: str) -> list[object]:
    return [
        value
        for branch_outputs in run.outputs.values()
        for value in branch_outputs.get(task_name, [])
    ]


@pytest.mark.asyncio
async def test_scoped_join_waits_for_its_descendants_and_resumes_owner_context():
    timeline: list[str] = []

    class ReviewContext(BaseModel):
        total: int = 0

    @task
    def begin() -> int:
        return 2

    @task
    async def contribute(value: int) -> int:
        await asyncio.sleep(0)
        timeline.append("contribute")
        return value + 1

    @task
    async def audit(value: int) -> None:
        await asyncio.sleep(0.01)
        timeline.append("audit")

    @task
    async def merge(values: list[int], context: ReviewContext) -> tuple[int, str]:
        assert timeline == ["contribute", "audit"]
        context.total = sum(values)
        return context.total, "report"

    @task
    def report(total: int, context: ReviewContext) -> tuple[int, int]:
        return total, context.total

    run = await Workflow(
        "scoped_join",
        context=ReviewContext,
        start=Node(run=begin, next=["contribute", "audit"]),
        contribute=Node(run=contribute, next="merged"),
        audit=audit,
        merged=Join(
            run=merge,
            scope="start",
            bind_output=["total", "route"],
            route_on="route",
            next={"report": "result"},
        ),
        result=Node(run=report),
    ).run()

    assert run.result == (3, 3)
    assert run.context == ReviewContext(total=3)
    assert _recorded_outputs(run, "merge") == [(3, "report")]


@pytest.mark.asyncio
async def test_repeated_scope_activations_reduce_independently():
    @task
    async def emit_values():
        yield 1
        yield 10

    @task
    def begin_family(value: int) -> int:
        return value

    @task
    async def add_one(value: int) -> int:
        await asyncio.sleep(0.01)
        return value + 1

    @task
    async def add_two(value: int) -> int:
        await asyncio.sleep(0)
        return value + 2

    @task
    def merge_family(values: list[int]) -> int:
        return sum(values)

    run = await Workflow(
        "repeated_scopes",
        start=Node(run=emit_values, next="family"),
        family=Node(run=begin_family, next=["add_one", "add_two"]),
        add_one=Node(run=add_one, next="family_result"),
        add_two=Node(run=add_two, next="family_result"),
        family_result=Join(
            run=merge_family,
            scope="family",
            next="result",
        ),
        result=Join(),
    ).run()

    assert sorted(run.result) == [5, 23]
    assert sorted(_recorded_outputs(run, "merge_family")) == [5, 23]


@pytest.mark.asyncio
async def test_generator_scope_closes_only_after_generator_exhaustion():
    reducer_calls: list[list[int]] = []

    @task
    async def emit_values():
        yield 1
        await asyncio.sleep(0)
        yield 2

    @task
    async def double(value: int) -> int:
        await asyncio.sleep(0)
        return value * 2

    @task
    def merge(values: list[int]) -> int:
        reducer_calls.append(values)
        return sum(values)

    @task
    def finish(value: int) -> int:
        return value

    run = await Workflow(
        "generator_scope",
        start=Node(run=emit_values, next="double"),
        double=Node(run=double, next="merged"),
        merged=Join(run=merge, scope="start", next="result"),
        result=Node(run=finish),
    ).run()

    assert run.result == 6
    assert len(reducer_calls) == 1
    assert sorted(reducer_calls[0]) == [2, 4]


@pytest.mark.asyncio
async def test_nested_scoped_joins_settle_inner_before_outer():
    reductions: list[str] = []

    @task
    def begin() -> int:
        return 1

    @task
    def pass_value(value: int) -> int:
        return value

    @task
    def add_one(value: int) -> int:
        return value + 1

    @task
    def add_two(value: int) -> int:
        return value + 2

    @task
    def outer_value(value: int) -> int:
        return value + 9

    @task
    def merge_inner(values: list[int]) -> int:
        reductions.append("inner")
        return sum(values)

    @task
    def merge_outer(values: list[int]) -> int:
        reductions.append("outer")
        return sum(values)

    @task
    def finish(value: int) -> int:
        return value

    run = await Workflow(
        "nested_scopes",
        start=Node(run=begin, next=["inner", "outer_value"]),
        inner=Node(run=pass_value, next=["add_one", "add_two"]),
        add_one=Node(run=add_one, next="inner_result"),
        add_two=Node(run=add_two, next="inner_result"),
        inner_result=Join(run=merge_inner, scope="inner", next="outer_result"),
        outer_value=Node(run=outer_value, next="outer_result"),
        outer_result=Join(run=merge_outer, scope="start", next="result"),
        result=Node(run=finish),
    ).run()

    assert run.result == 15
    assert reductions == ["inner", "outer"]


@pytest.mark.asyncio
async def test_scoped_join_reducer_receives_empty_contributions():
    @task
    def begin() -> str:
        return "work"

    @task
    def audit(value: str) -> str:
        return f"audit:{value}"

    @task
    def count(values: list[str]) -> int:
        return len(values)

    @task
    def finish(value: int) -> int:
        return value

    run = await Workflow(
        "empty_scoped_join",
        start=Node(run=begin, next="audit"),
        audit=audit,
        merged=Join(run=count, scope="start", next="result"),
        result=Node(run=finish),
    ).run()

    assert run.result == 0


def test_scoped_join_declaration_validation():
    @task
    def work() -> int:
        return 1

    with pytest.raises(TypeError, match="outside.*requires.*scope"):
        Workflow(
            "unscoped_mid_graph_join",
            start=work,
            merged=Join(run=work),
        )

    with pytest.raises(TypeError, match="reserved result.*terminal"):
        Workflow(
            "continuing_result_join",
            start=Node(run=work, next="result"),
            result=Join(next="after"),
            after=work,
        )

    with pytest.raises(TypeError, match="multiple joins.*scope 'start'"):
        Workflow(
            "duplicate_scope_join",
            start=work,
            first=Join(scope="start"),
            second=Join(scope="start"),
        )


@pytest.mark.asyncio
async def test_branch_cannot_reach_join_without_its_scope_membership():
    @task
    def work() -> int:
        return 1

    workflow = Workflow(
        "missing_scope_membership",
        start=Node(run=work, next="merged"),
        unused_scope=work,
        merged=Join(scope="unused_scope", next="result"),
        result=Node(run=work),
    )

    with pytest.raises(RuntimeError, match="without active scope"):
        await workflow.run()


@pytest.mark.asyncio
async def test_terminal_scoped_join_requires_exactly_one_scope_activation():
    @task
    async def emit_values():
        yield 1
        yield 2

    @task
    def family(value: int) -> int:
        return value

    repeated = Workflow(
        "repeated_terminal_scope",
        start=Node(run=emit_values, next="family"),
        family=Node(run=family, next="result"),
        result=Join(scope="family"),
    )

    with pytest.raises(RuntimeError, match="terminal.*activated more than once"):
        await repeated.run()

    @task
    def finish() -> int:
        return 1

    missing = Workflow(
        "missing_terminal_scope",
        start=finish,
        unused_scope=finish,
        result=Join(scope="unused_scope"),
    )

    with pytest.raises(RuntimeError, match="terminal.*did not activate"):
        await missing.run()


@pytest.mark.asyncio
async def test_same_join_scope_cannot_reenter_on_one_branch():
    calls = 0

    @task
    def begin() -> int:
        return 0

    @task
    def loop(value: int) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"value": value + 1, "route": "again"}

    workflow = Workflow(
        "scope_reentry",
        policy=WorkflowPolicy(allow_cycles=True),
        start=Node(run=begin, next="loop"),
        loop=Node(
            run=loop,
            route_on="route",
            next={"again": "loop", "done": "merged"},
        ),
        merged=Join(scope="loop", next="result"),
        result=Join(),
    )

    with pytest.raises(RuntimeError, match="re-enter.*before.*settled"):
        await workflow.run()

    assert calls == 1
