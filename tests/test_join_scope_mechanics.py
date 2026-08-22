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
async def test_scoped_join_reducer_mutates_owner_context_for_its_continuation():
    class State(BaseModel):
        total: int = 0

    @task
    def begin() -> int:
        return 2

    @task
    def increment(value: int) -> int:
        return value + 1

    @task
    def merge(values: list[int], context: State) -> int:
        context.total = sum(values)
        return context.total

    @task
    def finish(value: int, context: State) -> tuple[int, int]:
        return value, context.total

    run = await Workflow(
        "scoped_join_context",
        context=State,
        start=Node(run=begin, next="increment"),
        increment=Node(run=increment, next="merged"),
        merged=Join(run=merge, scope="start", next="result"),
        result=Node(run=finish),
    ).run()

    assert run.result == (3, 3)
    assert run.context == State(total=3)


@pytest.mark.asyncio
async def test_scoped_join_binds_and_routes_its_raw_reducer_output():
    @task
    def begin() -> int:
        return 2

    @task
    def increment(value: int) -> int:
        return value + 1

    @task
    def merge(values: list[int]) -> tuple[int, str]:
        return sum(values), "positive"

    @task
    def finish(total: int) -> int:
        return total

    run = await Workflow(
        "scoped_join_routing",
        start=Node(run=begin, next="increment"),
        increment=Node(run=increment, next="merged"),
        merged=Join(
            run=merge,
            scope="start",
            bind_output=["total", "route"],
            route_on="route",
            next={"positive": "result"},
        ),
        result=Node(run=finish),
    ).run()

    assert run.result == 3
    assert _recorded_outputs(run, "merge") == [(3, "positive")]


@pytest.mark.asyncio
async def test_reducerless_scoped_join_emits_its_contribution_list():
    @task
    def begin() -> int:
        return 1

    @task
    def add_one(value: int) -> int:
        return value + 1

    @task
    def add_two(value: int) -> int:
        return value + 2

    @task
    def finish(values: list[int]) -> list[int]:
        return sorted(values)

    run = await Workflow(
        "reducerless_scoped_join",
        start=Node(run=begin, next=["add_one", "add_two"]),
        add_one=Node(run=add_one, next="merged"),
        add_two=Node(run=add_two, next="merged"),
        merged=Join(scope="start", next="result"),
        result=Node(run=finish),
    ).run()

    assert run.result == [2, 3]


def test_mid_graph_join_requires_an_explicit_scope():
    @task
    def work() -> int:
        return 1

    with pytest.raises(TypeError, match="outside.*requires.*scope"):
        Workflow(
            "unscoped_mid_graph_join",
            start=work,
            merged=Join(run=work),
        )


def test_reserved_result_join_must_be_terminal():
    @task
    def work() -> int:
        return 1

    with pytest.raises(TypeError, match="reserved result.*terminal"):
        Workflow(
            "continuing_result_join",
            start=Node(run=work, next="result"),
            result=Join(next="after"),
            after=work,
        )


def test_scope_can_have_at_most_one_scoped_join():
    @task
    def work() -> int:
        return 1

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
async def test_terminal_scoped_join_rejects_repeated_scope_activations():
    @task
    async def emit_values():
        yield 1
        yield 2

    @task
    def family(value: int) -> int:
        return value

    workflow = Workflow(
        "repeated_terminal_scope",
        start=Node(run=emit_values, next="family"),
        family=Node(run=family, next="result"),
        result=Join(scope="family"),
    )

    with pytest.raises(RuntimeError, match="terminal.*activated more than once"):
        await workflow.run()


@pytest.mark.asyncio
async def test_terminal_scoped_join_rejects_missing_scope_activation():
    @task
    def finish() -> int:
        return 1

    workflow = Workflow(
        "missing_terminal_scope",
        start=finish,
        unused_scope=finish,
        result=Join(scope="unused_scope"),
    )

    with pytest.raises(RuntimeError, match="terminal.*did not activate"):
        await workflow.run()


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
