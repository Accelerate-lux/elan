"""Scoped-join scenarios organized by workflow graph shape."""

import asyncio
from unittest.mock import Mock, call

import pytest

from elan import Join, Node, When, Workflow, task


def _abstract_task(name, fn):
    fn.__name__ = name
    fn.__qualname__ = name
    return task(fn)


def _assert_calls(task_, *expected, any_order: bool = False) -> None:
    task_.mock.assert_has_calls(list(expected), any_order=any_order)
    assert task_.mock.call_count == len(expected)


def _assert_list_call(task_, expected: list[int]) -> None:
    task_.mock.assert_called_once()
    assert sorted(task_.mock.call_args.args[0]) == sorted(expected)


def _assert_called_once(*tasks) -> None:
    for task_ in tasks:
        task_.mock.assert_called_once()


def _call_position(manager: Mock, expected) -> int:
    return manager.mock_calls.index(expected)


def _first_task_position(manager: Mock, task_name: str) -> int:
    return next(
        index
        for index, recorded_call in enumerate(manager.mock_calls)
        if recorded_call[0] == task_name
    )


def _assert_before(manager: Mock, *events) -> None:
    positions = [
        _first_task_position(manager, event)
        if isinstance(event, str)
        else _call_position(manager, event)
        for event in events
    ]
    assert positions == sorted(positions)


@pytest.mark.asyncio
async def test_balanced_fork_waits_for_contributors_and_noncontributors(spy_tasks):
    """start -> [left -> join, right -> join, side] -> end."""
    completed: set[str] = set()

    begin = _abstract_task("begin", lambda: 1)

    @task
    async def left(value: int) -> int:
        await asyncio.sleep(0)
        completed.add("left")
        return value + 1

    @task
    async def right(value: int) -> int:
        await asyncio.sleep(0)
        completed.add("right")
        return value + 2

    @task
    async def side(value: int) -> int:
        await asyncio.sleep(0)
        completed.add("side")
        return value

    @task
    def merge(values: list[int]) -> list[int]:
        assert completed == {"left", "right", "side"}
        return sorted(values)

    finish = _abstract_task("finish", lambda values: values)

    task_calls = spy_tasks(begin, left, right, side, merge, finish)

    run = await Workflow(
        "balanced_fork",
        start=Node(run=begin, next=["left", "right", "side"]),
        left=Node(run=left, next="merged"),
        right=Node(run=right, next="merged"),
        side=side,
        merged=Join(run=merge, scope="start", next="result"),
        result=Node(run=finish),
    ).run()

    _assert_called_once(begin, left, right, side, merge, finish)
    _assert_before(task_calls, "begin", "left", "merge", "finish")
    _assert_before(task_calls, "begin", "right", "merge")
    _assert_before(task_calls, "begin", "side", "merge")
    assert run.result == [2, 3]


@pytest.mark.asyncio
async def test_fork_with_unequal_branch_depths(spy_tasks):
    """start -> [shallow -> join, deep_a -> deep_b -> join] -> end."""
    begin = _abstract_task("begin", lambda: 1)
    shallow = _abstract_task("shallow", lambda value: value + 10)
    deep_a = _abstract_task("deep_a", lambda value: value + 1)
    deep_b = _abstract_task("deep_b", lambda value: value * 10)
    merge = _abstract_task("merge", lambda values: sorted(values))
    finish = _abstract_task("finish", lambda values: values)

    task_calls = spy_tasks(begin, shallow, deep_a, deep_b, merge, finish)

    run = await Workflow(
        "unequal_depths",
        start=Node(run=begin, next=["shallow", "deep_a"]),
        shallow=Node(run=shallow, next="merged"),
        deep_a=Node(run=deep_a, next="deep_b"),
        deep_b=Node(run=deep_b, next="merged"),
        merged=Join(run=merge, scope="start", next="result"),
        result=Node(run=finish),
    ).run()

    _assert_called_once(begin, shallow, deep_a, deep_b, merge, finish)
    _assert_before(task_calls, "begin", "shallow", "merge", "finish")
    _assert_before(task_calls, "begin", "deep_a", "deep_b", "merge")
    assert run.result == [11, 20]


@pytest.mark.asyncio
async def test_nested_fan_out_inside_one_scope(spy_tasks):
    """start -> [left -> join, split -> [middle, right] -> join] -> end."""
    begin = _abstract_task("begin", lambda: 1)
    left = _abstract_task("left", lambda value: value + 1)
    split = _abstract_task("split", lambda value: value)
    middle = _abstract_task("middle", lambda value: value + 2)
    right = _abstract_task("right", lambda value: value + 3)
    merge = _abstract_task("merge", lambda values: sorted(values))
    finish = _abstract_task("finish", lambda values: values)

    task_calls = spy_tasks(begin, left, split, middle, right, merge, finish)

    run = await Workflow(
        "nested_fan_out",
        start=Node(run=begin, next=["left", "split"]),
        left=Node(run=left, next="merged"),
        split=Node(run=split, next=["middle", "right"]),
        middle=Node(run=middle, next="merged"),
        right=Node(run=right, next="merged"),
        merged=Join(run=merge, scope="start", next="result"),
        result=Node(run=finish),
    ).run()

    _assert_called_once(begin, left, split, middle, right, merge, finish)
    _assert_before(task_calls, "begin", "left", "merge", "finish")
    _assert_before(task_calls, "begin", "split", "middle", "merge")
    _assert_before(task_calls, "split", "right", "merge")
    assert run.result == [2, 3, 4]


@pytest.mark.asyncio
async def test_diamond_executes_shared_downstream_node_per_branch(spy_tasks):
    """start -> [left, right] -> shared -> join -> end."""
    begin = _abstract_task("begin", lambda: 1)
    left = _abstract_task("left", lambda value: value + 1)
    right = _abstract_task("right", lambda value: value + 2)
    shared = _abstract_task("shared", lambda value: value * 2)
    merge = _abstract_task("merge", lambda values: sorted(values))
    finish = _abstract_task("finish", lambda values: values)

    task_calls = spy_tasks(begin, left, right, shared, merge, finish)

    run = await Workflow(
        "diamond",
        start=Node(run=begin, next=["left", "right"]),
        left=Node(run=left, next="shared"),
        right=Node(run=right, next="shared"),
        shared=Node(run=shared, next="merged"),
        merged=Join(run=merge, scope="start", next="result"),
        result=Node(run=finish),
    ).run()

    _assert_called_once(begin, left, right, merge, finish)
    _assert_calls(shared, call(2), call(3), any_order=True)
    _assert_before(task_calls, "left", call.shared(2), "merge")
    _assert_before(task_calls, "right", call.shared(3), "merge")
    _assert_before(task_calls, "merge", "finish")
    assert run.result == [4, 6]


@pytest.mark.asyncio
async def test_conditional_fan_out_tracks_only_selected_descendants(spy_tasks):
    """start -> [When(left), When(right), side], selected -> join -> end."""
    begin = _abstract_task("begin", lambda: (2, True, False))
    left = _abstract_task("left", lambda value: value + 1)
    right = _abstract_task("right", lambda value: value + 2)
    side = _abstract_task("side", lambda value: value)
    merge = _abstract_task("merge", lambda values: values)
    finish = _abstract_task("finish", lambda values: values)

    task_calls = spy_tasks(begin, left, right, side, merge, finish)

    run = await Workflow(
        "conditional_fan_out",
        start=Node(
            run=begin,
            bind_output=["value", "take_left", "take_right"],
            next=[
                When("take_left", "left"),
                When("take_right", "right"),
                "side",
            ],
        ),
        left=Node(run=left, next="merged"),
        right=Node(run=right, next="merged"),
        side=side,
        merged=Join(run=merge, scope="start", next="result"),
        result=Node(run=finish),
    ).run()

    _assert_called_once(begin, left, side, merge, finish)
    left.mock.assert_called_once_with(value=2)
    right.mock.assert_not_called()
    _assert_before(task_calls, "begin", "left", "merge", "finish")
    _assert_before(task_calls, "begin", "side", "merge")
    assert run.result == [3]


@pytest.mark.asyncio
async def test_scope_owner_can_contribute_alongside_child_branches(spy_tasks):
    """start -> [join, left -> join, right -> join] -> end."""
    begin = _abstract_task("begin", lambda: 1)
    left = _abstract_task("left", lambda value: value + 1)
    right = _abstract_task("right", lambda value: value + 2)
    merge = _abstract_task("merge", lambda values: sorted(values))
    finish = _abstract_task("finish", lambda values: values)

    task_calls = spy_tasks(begin, left, right, merge, finish)

    run = await Workflow(
        "owner_contribution",
        start=Node(run=begin, next=["merged", "left", "right"]),
        left=Node(run=left, next="merged"),
        right=Node(run=right, next="merged"),
        merged=Join(run=merge, scope="start", next="result"),
        result=Node(run=finish),
    ).run()

    _assert_called_once(begin, left, right, merge, finish)
    _assert_before(task_calls, "begin", "left", "merge", "finish")
    _assert_before(task_calls, "begin", "right", "merge")
    assert run.result == [1, 2, 3]


@pytest.mark.asyncio
async def test_generator_scope_with_zero_one_and_many_yields(spy_tasks):
    """generator(scope) -> item -> join -> end, for 0, 1, and many items."""
    reducer_calls: list[list[int]] = []

    @task
    async def emit(count: int):
        for value in range(count):
            yield value

    double = _abstract_task("double", lambda value: value * 2)

    @task
    def merge(values: list[int]) -> list[int]:
        reducer_calls.append(sorted(values))
        return sorted(values)

    finish = _abstract_task("finish", lambda values: values)

    spy_tasks(emit, double, merge, finish)

    workflow = Workflow(
        "generator_scope",
        start=Node(run=emit, next="double"),
        double=Node(run=double, next="merged"),
        merged=Join(run=merge, scope="start", next="result"),
        result=Node(run=finish),
    )

    results = [
        (await workflow.run(count=count)).result
        for count in (0, 1, 3)
    ]

    assert results == [[], [0], [0, 2, 4]]
    assert reducer_calls == results
    _assert_calls(emit, call(count=0), call(count=1), call(count=3))
    _assert_calls(
        double,
        call(0),
        call(0),
        call(1),
        call(2),
        any_order=True,
    )
    assert [sorted(item.args[0]) for item in merge.mock.call_args_list] == results
    assert finish.mock.call_count == 3


@pytest.mark.asyncio
async def test_descendant_generator_keeps_scope_open_until_exhaustion(spy_tasks):
    """start -> [generator -> item -> join, side -> join] -> end."""
    begin = _abstract_task("begin", lambda: 1)

    @task
    async def emit(value: int):
        yield value
        await asyncio.sleep(0)
        yield value + 1

    double = _abstract_task("double", lambda value: value * 2)
    side = _abstract_task("side", lambda value: value + 9)
    merge = _abstract_task("merge", lambda values: sorted(values))
    finish = _abstract_task("finish", lambda values: values)

    task_calls = spy_tasks(begin, emit, double, side, merge, finish)

    run = await Workflow(
        "descendant_generator",
        start=Node(run=begin, next=["emit", "side"]),
        emit=Node(run=emit, next="double"),
        double=Node(run=double, next="merged"),
        side=Node(run=side, next="merged"),
        merged=Join(run=merge, scope="start", next="result"),
        result=Node(run=finish),
    ).run()

    _assert_called_once(begin, emit, side, merge, finish)
    _assert_calls(double, call(1), call(2), any_order=True)
    _assert_list_call(merge, [2, 4, 10])
    _assert_before(task_calls, "emit", call.double(1), "merge")
    _assert_before(task_calls, "emit", call.double(2), "merge")
    _assert_before(task_calls, "begin", "side", "merge", "finish")
    assert run.result == [2, 4, 10]


@pytest.mark.asyncio
async def test_repeated_scope_instances_can_overlap_without_mixing_values(spy_tasks):
    """generator -> scope(value) -> join, with two scope instances in flight."""
    both_instances_active = asyncio.Event()
    arrivals = 0

    @task
    async def emit():
        yield 1
        yield 10

    open_scope = _abstract_task("open_scope", lambda value: value)

    @task
    async def contribute(value: int) -> int:
        nonlocal arrivals
        arrivals += 1
        if arrivals == 2:
            both_instances_active.set()
        await both_instances_active.wait()
        return value + 1

    merge = _abstract_task("merge", lambda values: values[0])

    spy_tasks(emit, open_scope, contribute, merge)

    run = await Workflow(
        "overlapping_instances",
        start=Node(run=emit, next="open_scope"),
        open_scope=Node(run=open_scope, next="contribute"),
        contribute=Node(run=contribute, next="family_result"),
        family_result=Join(run=merge, scope="open_scope", next="result"),
        result=Join(),
    ).run()

    assert arrivals == 2
    assert sorted(run.result) == [2, 11]
    emit.mock.assert_called_once_with()
    _assert_calls(open_scope, call(1), call(10), any_order=True)
    _assert_calls(contribute, call(1), call(10), any_order=True)
    assert sorted(item.args[0] for item in merge.mock.call_args_list) == [[2], [11]]


@pytest.mark.asyncio
async def test_nested_scopes_settle_inner_before_outer(spy_tasks):
    """outer(scope) -> [inner(scope) -> inner_join, side] -> outer_join -> end."""
    reductions: list[str] = []

    begin = _abstract_task("begin", lambda: 1)
    open_inner = _abstract_task("open_inner", lambda value: value)
    add_one = _abstract_task("add_one", lambda value: value + 1)
    add_two = _abstract_task("add_two", lambda value: value + 2)
    side = _abstract_task("side", lambda value: value + 9)

    @task
    def merge_inner(values: list[int]) -> int:
        reductions.append("inner")
        return sum(values)

    @task
    def merge_outer(values: list[int]) -> int:
        reductions.append("outer")
        return sum(values)

    finish = _abstract_task("finish", lambda value: value)

    task_calls = spy_tasks(
        begin,
        open_inner,
        add_one,
        add_two,
        side,
        merge_inner,
        merge_outer,
        finish,
    )

    run = await Workflow(
        "nested_scopes",
        start=Node(run=begin, next=["open_inner", "side"]),
        open_inner=Node(run=open_inner, next=["add_one", "add_two"]),
        add_one=Node(run=add_one, next="inner_result"),
        add_two=Node(run=add_two, next="inner_result"),
        inner_result=Join(run=merge_inner, scope="open_inner", next="outer_result"),
        side=Node(run=side, next="outer_result"),
        outer_result=Join(run=merge_outer, scope="start", next="result"),
        result=Node(run=finish),
    ).run()

    _assert_called_once(
        begin, open_inner, add_one, add_two, side, merge_inner, merge_outer, finish
    )
    _assert_list_call(merge_inner, [2, 3])
    _assert_list_call(merge_outer, [5, 10])
    _assert_before(task_calls, "begin", "open_inner", "add_one", "merge_inner")
    _assert_before(task_calls, "open_inner", "add_two", "merge_inner")
    _assert_before(task_calls, "begin", "side", "merge_outer", "finish")
    _assert_before(task_calls, "merge_inner", "merge_outer")
    assert run.result == 15
    assert reductions == ["inner", "outer"]


@pytest.mark.asyncio
async def test_sequential_scopes_open_and_settle_in_order(spy_tasks):
    """first(scope) -> first_join -> second(scope) -> second_join -> end."""
    reductions: list[str] = []

    begin = _abstract_task("begin", lambda: 1)
    add_one = _abstract_task("add_one", lambda value: value + 1)
    add_two = _abstract_task("add_two", lambda value: value + 2)

    @task
    def merge_first(values: list[int]) -> int:
        reductions.append("first")
        return sum(values)

    open_second = _abstract_task("open_second", lambda value: value)
    double = _abstract_task("double", lambda value: value * 2)
    triple = _abstract_task("triple", lambda value: value * 3)

    @task
    def merge_second(values: list[int]) -> int:
        reductions.append("second")
        return sum(values)

    finish = _abstract_task("finish", lambda value: value)

    task_calls = spy_tasks(
        begin,
        add_one,
        add_two,
        merge_first,
        open_second,
        double,
        triple,
        merge_second,
        finish,
    )

    run = await Workflow(
        "sequential_scopes",
        start=Node(run=begin, next=["add_one", "add_two"]),
        add_one=Node(run=add_one, next="first_result"),
        add_two=Node(run=add_two, next="first_result"),
        first_result=Join(run=merge_first, scope="start", next="open_second"),
        open_second=Node(run=open_second, next=["double", "triple"]),
        double=Node(run=double, next="second_result"),
        triple=Node(run=triple, next="second_result"),
        second_result=Join(run=merge_second, scope="open_second", next="result"),
        result=Node(run=finish),
    ).run()

    _assert_called_once(
        begin,
        add_one,
        add_two,
        merge_first,
        open_second,
        double,
        triple,
        merge_second,
        finish,
    )
    _assert_before(
        task_calls,
        "begin",
        "add_one",
        "merge_first",
        "open_second",
        "double",
        "merge_second",
        "finish",
    )
    _assert_before(task_calls, "begin", "add_two", "merge_first")
    _assert_before(task_calls, "open_second", "triple", "merge_second")
    assert run.result == 25
    assert reductions == ["first", "second"]


@pytest.mark.asyncio
async def test_concurrent_sibling_scopes_settle_independently(spy_tasks):
    """start -> [left(scope) -> left_join, right(scope) -> right_join] -> result."""
    begin = _abstract_task("begin", lambda: 1)
    open_left = _abstract_task("open_left", lambda value: value)
    open_right = _abstract_task("open_right", lambda value: value)
    left_a = _abstract_task("left_a", lambda value: value + 1)
    left_b = _abstract_task("left_b", lambda value: value + 2)
    right_a = _abstract_task("right_a", lambda value: value + 10)
    right_b = _abstract_task("right_b", lambda value: value + 20)
    total = _abstract_task("total", lambda values: sum(values))

    spy_tasks(
        begin,
        open_left,
        open_right,
        left_a,
        left_b,
        right_a,
        right_b,
        total,
    )

    run = await Workflow(
        "sibling_scopes",
        start=Node(run=begin, next=["open_left", "open_right"]),
        open_left=Node(run=open_left, next=["left_a", "left_b"]),
        left_a=Node(run=left_a, next="left_result"),
        left_b=Node(run=left_b, next="left_result"),
        left_result=Join(run=total, scope="open_left", next="result"),
        open_right=Node(run=open_right, next=["right_a", "right_b"]),
        right_a=Node(run=right_a, next="right_result"),
        right_b=Node(run=right_b, next="right_result"),
        right_result=Join(run=total, scope="open_right", next="result"),
        result=Join(),
    ).run()

    _assert_called_once(
        begin, open_left, open_right, left_a, left_b, right_a, right_b
    )
    assert sorted(
        sorted(item.args[0]) for item in total.mock.call_args_list
    ) == [[2, 3], [11, 21]]
    assert sorted(run.result) == [5, 32]


@pytest.mark.asyncio
async def test_join_continuation_can_fan_out_again(spy_tasks):
    """scope -> [left, right] -> join -> [double, triple] -> result."""
    begin = _abstract_task("begin", lambda: 1)
    add_one = _abstract_task("add_one", lambda value: value + 1)
    add_two = _abstract_task("add_two", lambda value: value + 2)
    total = _abstract_task("total", lambda values: sum(values))
    double = _abstract_task("double", lambda value: value * 2)
    triple = _abstract_task("triple", lambda value: value * 3)

    task_calls = spy_tasks(begin, add_one, add_two, total, double, triple)

    run = await Workflow(
        "join_continuation_fan_out",
        start=Node(run=begin, next=["add_one", "add_two"]),
        add_one=Node(run=add_one, next="merged"),
        add_two=Node(run=add_two, next="merged"),
        merged=Join(run=total, scope="start", next=["double", "triple"]),
        double=Node(run=double, next="result"),
        triple=Node(run=triple, next="result"),
        result=Join(),
    ).run()

    _assert_called_once(begin, add_one, add_two, total, double, triple)
    _assert_before(task_calls, "begin", "add_one", "total", "double")
    _assert_before(task_calls, "begin", "add_two", "total", "triple")
    assert sorted(run.result) == [10, 15]


@pytest.mark.asyncio
async def test_scoped_join_inside_child_workflow_composes_with_parent(spy_tasks):
    """parent -> child(scope -> [left, right] -> join -> end)."""
    prepare = _abstract_task("prepare", lambda: 1)
    child_start = _abstract_task("child_start", lambda value: value)
    left = _abstract_task("left", lambda value: value + 1)
    right = _abstract_task("right", lambda value: value + 2)
    total = _abstract_task("total", lambda values: sum(values))
    finish = _abstract_task("finish", lambda value: value * 2)

    task_calls = spy_tasks(prepare, child_start, left, right, total, finish)

    child = Workflow(
        "scoped_child",
        start=Node(run=child_start, next=["left", "right"]),
        left=Node(run=left, next="merged"),
        right=Node(run=right, next="merged"),
        merged=Join(run=total, scope="start", next="result"),
        result=Node(run=finish),
    )

    run = await Workflow(
        "parent_of_scoped_child",
        start=Node(run=prepare, next="child"),
        child=Node(run=child),
    ).run()

    _assert_called_once(prepare, child_start, left, right, total, finish)
    _assert_before(task_calls, "prepare", "child_start", "left", "total", "finish")
    _assert_before(task_calls, "child_start", "right", "total")
    assert run.result == 10


@pytest.mark.asyncio
async def test_terminal_scoped_join_reduces_one_scope_activation(spy_tasks):
    """scope -> [left, right] -> terminal scoped join."""
    begin = _abstract_task("begin", lambda: 1)
    left = _abstract_task("left", lambda value: value + 1)
    right = _abstract_task("right", lambda value: value + 2)
    total = _abstract_task("total", lambda values: sum(values))

    task_calls = spy_tasks(begin, left, right, total)

    run = await Workflow(
        "terminal_scoped_join",
        start=Node(run=begin, next=["left", "right"]),
        left=Node(run=left, next="result"),
        right=Node(run=right, next="result"),
        result=Join(run=total, scope="start"),
    ).run()

    _assert_called_once(begin, left, right, total)
    _assert_before(task_calls, "begin", "left", "total")
    _assert_before(task_calls, "begin", "right", "total")
    assert run.result == 5


@pytest.mark.asyncio
async def test_balanced_fork_with_two_steps_per_branch(spy_tasks):
    """start -> [left_a -> left_b, right_a -> right_b] -> join -> end."""
    begin = _abstract_task("begin", lambda: 1)
    left_a = _abstract_task("left_a", lambda value: value + 1)
    left_b = _abstract_task("left_b", lambda value: value * 2)
    right_a = _abstract_task("right_a", lambda value: value + 2)
    right_b = _abstract_task("right_b", lambda value: value * 3)
    merge = _abstract_task("merge", lambda values: sorted(values))
    finish = _abstract_task("finish", lambda values: values)

    task_calls = spy_tasks(begin, left_a, left_b, right_a, right_b, merge, finish)

    run = await Workflow(
        "balanced_two_step_fork",
        start=Node(run=begin, next=["left_a", "right_a"]),
        left_a=Node(run=left_a, next="left_b"),
        left_b=Node(run=left_b, next="merged"),
        right_a=Node(run=right_a, next="right_b"),
        right_b=Node(run=right_b, next="merged"),
        merged=Join(run=merge, scope="start", next="result"),
        result=Node(run=finish),
    ).run()

    _assert_called_once(begin, left_a, left_b, right_a, right_b, merge, finish)
    _assert_before(task_calls, call.left_a(1), call.left_b(2), "merge", "finish")
    _assert_before(task_calls, call.right_a(1), call.right_b(3), "merge")
    assert run.result == [4, 9]


@pytest.mark.asyncio
async def test_generated_items_pass_through_two_steps_before_one_join(spy_tasks):
    """generator(scope) -> item_a -> item_b -> join -> end."""
    @task
    async def emit():
        yield 1
        yield 2
        yield 3

    item_a = _abstract_task("item_a", lambda value: value + 1)
    item_b = _abstract_task("item_b", lambda value: value * 2)
    merge = _abstract_task("merge", lambda values: sorted(values))
    finish = _abstract_task("finish", lambda values: values)

    task_calls = spy_tasks(emit, item_a, item_b, merge, finish)

    run = await Workflow(
        "generated_two_step_items",
        start=Node(run=emit, next="item_a"),
        item_a=Node(run=item_a, next="item_b"),
        item_b=Node(run=item_b, next="merged"),
        merged=Join(run=merge, scope="start", next="result"),
        result=Node(run=finish),
    ).run()

    _assert_called_once(emit, merge, finish)
    _assert_calls(item_a, call(1), call(2), call(3), any_order=True)
    _assert_calls(item_b, call(2), call(3), call(4), any_order=True)
    for emitted_value in (1, 2, 3):
        _assert_before(
            task_calls,
            call.item_a(emitted_value),
            call.item_b(emitted_value + 1),
            "merge",
        )
    _assert_before(task_calls, "merge", "finish")
    assert run.result == [4, 6, 8]


@pytest.mark.asyncio
async def test_generated_local_scopes_feed_global_join_then_parent_continuation(
    spy_tasks,
):
    """generator -> repeated local scopes -> global join; parent -> end."""
    local_reductions: list[list[int]] = []

    @task
    async def emit():
        yield 1
        yield 10

    open_family = _abstract_task("open_family", lambda value: value)
    add_one = _abstract_task("add_one", lambda value: value + 1)
    add_two = _abstract_task("add_two", lambda value: value + 2)

    @task
    def merge_family(values: list[int]) -> int:
        local_reductions.append(sorted(values))
        return sum(values)

    continue_item = _abstract_task("continue_item", lambda value: value * 10)
    merge_all = _abstract_task("merge_all", lambda values: sum(values))

    batch = Workflow(
        "local_scopes_then_global_join",
        start=Node(run=emit, next="open_family"),
        open_family=Node(run=open_family, next=["add_one", "add_two"]),
        add_one=Node(run=add_one, next="family_result"),
        add_two=Node(run=add_two, next="family_result"),
        family_result=Join(
            run=merge_family,
            scope="open_family",
            next="continue_item",
        ),
        continue_item=Node(run=continue_item, next="result"),
        result=Join(run=merge_all),
    )

    seed = _abstract_task("seed", lambda: None)
    finish = _abstract_task("finish", lambda value: value + 1)

    task_calls = spy_tasks(
        emit,
        open_family,
        add_one,
        add_two,
        merge_family,
        continue_item,
        merge_all,
        seed,
        finish,
    )

    run = await Workflow(
        "global_join_parent_continuation",
        start=Node(run=seed, next="batch"),
        batch=Node(run=batch, next="finish"),
        finish=finish,
    ).run()

    _assert_called_once(seed, emit, merge_all, finish)
    _assert_calls(open_family, call(1), call(10), any_order=True)
    _assert_calls(add_one, call(1), call(10), any_order=True)
    _assert_calls(add_two, call(1), call(10), any_order=True)
    assert sorted(
        sorted(item.args[0]) for item in merge_family.mock.call_args_list
    ) == [[2, 3], [11, 12]]
    _assert_calls(continue_item, call(5), call(23), any_order=True)
    _assert_list_call(merge_all, [50, 230])

    _assert_before(task_calls, call.seed(), call.emit())
    for emitted_value in (1, 10):
        _assert_before(
            task_calls,
            call.open_family(emitted_value),
            call.add_one(emitted_value),
        )
        _assert_before(
            task_calls,
            call.open_family(emitted_value),
            call.add_two(emitted_value),
        )
    _assert_before(task_calls, call.continue_item(5), "merge_all", call.finish(280))
    _assert_before(task_calls, call.continue_item(23), "merge_all")

    assert sorted(local_reductions) == [[2, 3], [11, 12]]
    assert run.result == 281
