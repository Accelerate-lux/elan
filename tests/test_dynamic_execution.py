from collections.abc import Generator
from unittest.mock import Mock

import pytest
from pydantic import BaseModel

from elan import Expand, Fragment, Join, Node, When, Workflow, WorkflowPolicy, task


class Plan(BaseModel):
    value: int


@pytest.mark.asyncio
async def test_expand_materializes_fragment_and_routes_to_static_node():
    builder_inputs: list[Plan] = []

    @task
    def create_plan() -> Plan:
        return Plan(value=3)

    @task
    def prepare(plan: Plan) -> int:
        return plan.value + 1

    @task
    def process(value: int) -> int:
        return value * 2

    @task
    def finish(value: int) -> str:
        return f"value={value}"

    def build(plan: Plan) -> Fragment:
        builder_inputs.append(plan)
        return Fragment(
            start=Node(run=prepare, next="process"),
            process=Node(run=process, next="result"),
        )

    run = await Workflow(
        "dynamic",
        policy=WorkflowPolicy(allow_runtime_expansion=True),
        start=Node(run=create_plan, next=Expand(build)),
        result=Node(run=finish),
    ).run()

    assert builder_inputs == [Plan(value=3)]
    assert run.result == "value=8"
    assert all("build" not in outputs for outputs in run.outputs.values())


@pytest.mark.asyncio
async def test_expand_receives_bound_mapping_and_entry_receives_original_packet():
    builder_inputs: list[dict[str, int]] = []

    @task
    def emit() -> tuple[int, int]:
        return 2, 5

    @task
    def add(left: int, right: int) -> int:
        return left + right

    @task
    def finish(value: int) -> int:
        return value

    def build(packet: dict[str, int]) -> Fragment:
        builder_inputs.append(packet)
        return Fragment(start=Node(run=add, next="result"))

    run = await Workflow(
        "mapped_expansion",
        policy=WorkflowPolicy(allow_runtime_expansion=True),
        start=Node(
            run=emit,
            bind_output=["left", "right"],
            next=Expand(build),
        ),
        result=Node(run=finish),
    ).run()

    assert builder_inputs == [{"left": 2, "right": 5}]
    assert run.result == 7


@pytest.mark.asyncio
async def test_expand_is_rejected_by_policy_before_work_starts():
    start_call = Mock()

    @task
    def emit() -> int:
        start_call()
        return 1

    @task
    def passthrough(value: int) -> int:
        return value

    def build(value: int) -> Fragment:
        return Fragment(start=passthrough)

    workflow = Workflow(
        "expansion_disabled",
        start=Node(run=emit, next=Expand(build)),
    )

    with pytest.raises(TypeError, match="policy does not allow runtime expansion"):
        await workflow.run()
    start_call.assert_not_called()


def test_expand_rejects_incompatible_builder_signatures():
    @task
    def task_builder(value: int) -> Fragment:
        return Fragment(start="unused")

    async def async_builder(value: int) -> Fragment:
        return Fragment(start="unused")

    def generator_builder(value: int) -> Fragment:
        yield value

    def missing_parameter_annotation(value) -> Fragment:
        return Fragment(start="unused")

    def missing_return_annotation(value: int):
        return Fragment(start="unused")

    def wrong_return(value: int) -> int:
        return value

    def too_many(left: int, right: int) -> Fragment:
        return Fragment(start="unused")

    invalid = (
        task_builder,
        async_builder,
        generator_builder,
        missing_parameter_annotation,
        missing_return_annotation,
        wrong_return,
        too_many,
    )
    for builder in invalid:
        with pytest.raises(TypeError):
            Expand(builder)


def test_expand_must_be_the_complete_next_value():
    @task
    def emit() -> int:
        return 1

    def build(value: int) -> Fragment:
        return Fragment(start=emit)

    with pytest.raises(TypeError, match="complete next value"):
        Workflow(
            "nested_expand",
            start=Node(run=emit, next=[Expand(build)]),
        )


def test_fragment_rejects_local_result_boundary():
    @task
    def emit() -> int:
        return 1

    with pytest.raises(TypeError, match="cannot declare local node 'result'"):
        Fragment(start=emit, result=emit)


@pytest.mark.asyncio
async def test_expand_rejects_non_fragment_builder_return():
    @task
    def emit() -> int:
        return 1

    def build(value: int) -> Fragment:
        return value  # type: ignore[return-value]

    with pytest.raises(TypeError, match="returned int; expected Fragment"):
        await Workflow(
            "invalid_builder_return",
            policy=WorkflowPolicy(allow_runtime_expansion=True),
            start=Node(run=emit, next=Expand(build)),
        ).run()


@pytest.mark.asyncio
async def test_invalid_fragment_is_rejected_before_its_entry_is_scheduled():
    entry_call = Mock()

    @task
    def emit() -> int:
        return 1

    @task
    def entry(value: int) -> int:
        entry_call(value)
        return value

    def build(value: int) -> Fragment:
        return Fragment(start=Node(run=entry, next="missing"))

    with pytest.raises(KeyError, match="unknown lexical node 'missing'"):
        await Workflow(
            "atomic_expansion",
            policy=WorkflowPolicy(allow_runtime_expansion=True),
            start=Node(run=emit, next=Expand(build)),
        ).run()
    entry_call.assert_not_called()


@pytest.mark.asyncio
async def test_fragment_task_names_are_resolved_before_entry_scheduling():
    @task
    def emit() -> int:
        return 1

    def build(value: int) -> Fragment:
        return Fragment(start="missing-task")

    with pytest.raises(KeyError, match="Unknown task 'missing-task'"):
        await Workflow(
            "task_resolution",
            policy=WorkflowPolicy(allow_runtime_expansion=True),
            start=Node(run=emit, next=Expand(build)),
        ).run()


@pytest.mark.asyncio
async def test_fragment_static_cycle_respects_cycle_policy():
    cycle_call = Mock()

    @task
    def emit() -> int:
        return 1

    @task
    def cycle(value: int) -> int:
        cycle_call(value)
        return value

    def build(value: int) -> Fragment:
        return Fragment(start=Node(run=cycle, next="start"))

    with pytest.raises(TypeError, match="creates a static cycle"):
        await Workflow(
            "dynamic_cycle",
            policy=WorkflowPolicy(allow_runtime_expansion=True),
            start=Node(run=emit, next=Expand(build)),
        ).run()
    cycle_call.assert_not_called()


@pytest.mark.asyncio
async def test_fragment_static_cycle_can_be_allowed():
    @task
    def emit() -> int:
        return 1

    @task
    def stop(value: int) -> dict[str, bool | int]:
        return {"again": False, "done": True, "value": value}

    @task
    def finish(packets: list[dict[str, bool | int]]) -> int:
        return int(packets[0]["value"])

    def build(value: int) -> Fragment:
        return Fragment(
            start=Node(
                run=stop,
                next=[
                    When("again", "start"),
                    When("done", "result"),
                ],
            )
        )

    run = await Workflow(
        "allowed_dynamic_cycle",
        policy=WorkflowPolicy(
            allow_runtime_expansion=True,
            allow_cycles=True,
        ),
        start=Node(run=emit, next=Expand(build)),
        result=Join(run=finish),
    ).run()

    assert run.result == 1


@pytest.mark.asyncio
async def test_nested_expand_resolves_parent_fragment_nodes_lexically():
    @task
    def emit() -> int:
        return 2

    @task
    def outer_start(value: int) -> int:
        return value + 1

    @task
    def inner_start(value: int) -> int:
        return value * 4

    @task
    def parent_finish(value: int) -> str:
        return f"nested={value}"

    @task
    def finish(value: str) -> str:
        return value

    def build_inner(value: int) -> Fragment:
        return Fragment(start=Node(run=inner_start, next="parent_finish"))

    def build_outer(value: int) -> Fragment:
        return Fragment(
            start=Node(run=outer_start, next=Expand(build_inner)),
            parent_finish=Node(run=parent_finish, next="result"),
        )

    run = await Workflow(
        "nested_lexical_expansion",
        policy=WorkflowPolicy(allow_runtime_expansion=True),
        start=Node(run=emit, next=Expand(build_outer)),
        result=Node(run=finish),
    ).run()

    assert run.result == "nested=12"


@pytest.mark.asyncio
async def test_expanded_entry_preserves_current_branch_context():
    class RunContext(BaseModel):
        offset: int = 0

    @task
    def emit() -> int:
        return 2

    @task
    def read_context(value: int, context: RunContext) -> int:
        return value + context.offset

    @task
    def finish(value: int) -> int:
        return value

    def build(value: int) -> Fragment:
        return Fragment(start=Node(run=read_context, next="result"))

    run = await Workflow(
        "expanded_context",
        context=RunContext,
        policy=WorkflowPolicy(allow_runtime_expansion=True),
        start=Node(
            run=emit,
            context={"offset": 5},
            next=Expand(build),
        ),
        result=Node(run=finish),
    ).run()

    assert run.result == 7
    assert run.context == RunContext(offset=5)


@pytest.mark.asyncio
async def test_fragment_join_scope_must_belong_to_same_fragment():
    @task
    def emit() -> int:
        return 1

    def build(value: int) -> Fragment:
        return Fragment(
            start=Node(run=emit, next="joined"),
            joined=Join(scope="outside"),
        )

    with pytest.raises(TypeError, match="non-local scope 'outside'"):
        await Workflow(
            "non_local_fragment_scope",
            policy=WorkflowPolicy(allow_runtime_expansion=True),
            start=Node(run=emit, next=Expand(build)),
            outside=emit,
        ).run()


@pytest.mark.asyncio
async def test_fragment_defined_scoped_join_reduces_before_static_result():
    @task
    def emit() -> int:
        return 3

    @task
    def open_scope(value: int) -> int:
        return value

    @task
    def left(value: int) -> int:
        return value + 1

    @task
    def right(value: int) -> int:
        return value + 2

    @task
    def collect(values: list[int]) -> int:
        return sum(values)

    @task
    def finish(value: int) -> str:
        return f"sum={value}"

    def build(value: int) -> Fragment:
        return Fragment(
            start=Node(run=open_scope, next=["left", "right"]),
            left=Node(run=left, next="joined"),
            right=Node(run=right, next="joined"),
            joined=Join(run=collect, scope="start", next="result"),
        )

    run = await Workflow(
        "fragment_join",
        policy=WorkflowPolicy(allow_runtime_expansion=True),
        start=Node(run=emit, next=Expand(build)),
        result=Node(run=finish),
    ).run()

    assert run.result == "sum=9"


@pytest.mark.asyncio
async def test_recursive_expansion_materializes_finite_nested_fragments():
    @task
    def emit() -> int:
        return 3

    @task
    def decrement(value: int) -> int:
        return value - 1

    @task
    def passthrough(value: int) -> int:
        return value

    def build(value: int) -> Fragment:
        if value == 0:
            return Fragment(start=Node(run=passthrough, next="result"))
        return Fragment(start=Node(run=decrement, next=Expand(build)))

    run = await Workflow(
        "recursive_expansion",
        policy=WorkflowPolicy(allow_runtime_expansion=True),
        start=Node(run=emit, next=Expand(build)),
        result=Node(run=passthrough),
    ).run()

    assert run.result == 0


@pytest.mark.asyncio
async def test_reusable_fragment_is_isolated_across_generator_expansions():
    static_shadow = Mock()

    @task
    def generate() -> Generator[int, None, None]:
        yield 1
        yield 2
        yield 3

    @task
    def enter(value: int) -> int:
        return value

    @task
    def process(value: int) -> int:
        return value * 10

    @task
    def static_process(value: int) -> int:
        static_shadow(value)
        return -1

    @task
    def collect(values: list[int]) -> list[int]:
        return sorted(values)

    reusable = Fragment(
        start=Node(run=enter, next="process"),
        process=Node(run=process, next="result"),
    )

    def build(value: int) -> Fragment:
        return reusable

    run = await Workflow(
        "reusable_fragment",
        policy=WorkflowPolicy(allow_runtime_expansion=True),
        start=Node(run=generate, next=Expand(build)),
        process=Node(run=static_process, next="result"),
        result=Join(run=collect),
    ).run()

    static_shadow.assert_not_called()
    assert run.result == [10, 20, 30]
