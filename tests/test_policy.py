import asyncio

import pytest
from pydantic import BaseModel, Field

from elan import Binder, Join, Node, Policy, Workflow, WorkflowPolicy, task


@pytest.mark.asyncio
async def test_policy_field_can_bind_task_input(branch_id):
    @task
    def show_limit(limit: int) -> int:
        return limit

    run = await Workflow(
        "policy_binding",
        policy=WorkflowPolicy(max_parallel_tasks=3),
        start=Node(
            run=show_limit,
            bind_input=Binder[show_limit](limit=Policy.max_parallel_tasks),
        ),
    ).run()

    assert run.result == 3
    assert run.outputs == {
        branch_id[0]: {
            "show_limit": [3],
        }
    }


@pytest.mark.asyncio
async def test_workflow_subclass_can_declare_policy(branch_id):
    @task
    def show_limit(limit: int) -> int:
        return limit

    class LimitedWorkflow(Workflow):
        policy = WorkflowPolicy(max_parallel_tasks=4)
        start = Node(
            run=show_limit,
            bind_input=Binder[show_limit](limit=Policy.max_parallel_tasks),
        )

    workflow = LimitedWorkflow()
    run = await workflow.run()

    assert workflow.policy == WorkflowPolicy(max_parallel_tasks=4)
    assert workflow.nodes == {}
    assert run.result == 4
    assert run.outputs == {
        branch_id[0]: {
            "show_limit": [4],
        }
    }


def test_workflow_rejects_policy_class_instead_of_instance():
    @task
    def hello():
        return "hello"

    with pytest.raises(
        TypeError,
        match="Workflow policy must be a WorkflowPolicy instance or None",
    ):
        Workflow("policy_class", policy=WorkflowPolicy, start=hello)


@pytest.mark.asyncio
async def test_policy_field_can_bind_context(branch_id):
    class RunContext(BaseModel):
        limit: int

    @task
    def show_context(context: RunContext) -> int:
        return context.limit

    run = await Workflow(
        "policy_context_binding",
        policy=WorkflowPolicy(max_parallel_tasks=2),
        context=RunContext,
        bind_context=Binder[RunContext](limit=Policy.max_parallel_tasks),
        start=show_context,
    ).run()

    assert run.result == 2
    assert run.outputs == {
        branch_id[0]: {
            "show_context": [2],
        }
    }


@pytest.mark.asyncio
async def test_policy_max_parallel_tasks_limits_scheduler_concurrency():
    running = 0
    max_seen = 0

    @task
    def load():
        return "value"

    @task
    async def slow(value: str) -> str:
        nonlocal running, max_seen
        running += 1
        max_seen = max(max_seen, running)
        await asyncio.sleep(0.01)
        running -= 1
        return value

    @task
    def collect(values: list[str]) -> list[str]:
        return values

    run = await Workflow(
        "limited_parallelism",
        policy=WorkflowPolicy(max_parallel_tasks=1),
        start=Node(run=load, next=["one", "two", "three"]),
        one=Node(run=slow, next="result"),
        two=Node(run=slow, next="result"),
        three=Node(run=slow, next="result"),
        result=Join(run=collect),
    ).run()

    assert sorted(run.result) == ["value", "value", "value"]
    assert max_seen == 1


@pytest.mark.asyncio
async def test_child_workflow_inherits_parent_policy(branch_id):
    @task
    def load():
        return "start"

    @task
    def read_limit(value: str, limit: int) -> int:
        return len(value) + limit

    child = Workflow(
        "read_policy",
        start=Node(
            run=read_limit,
            bind_input=Binder[read_limit](limit=Policy.max_parallel_tasks),
        ),
    )

    run = await Workflow(
        "parent",
        policy=WorkflowPolicy(max_parallel_tasks=2),
        start=Node(run=load, next="child"),
        child=Node(run=child),
    ).run()

    assert run.result == 7
    assert run.outputs == {
        branch_id[0]: {
            "load": ["start"],
            "read_policy": [7],
        }
    }


@pytest.mark.asyncio
async def test_child_workflow_can_narrow_parent_policy(branch_id):
    @task
    def load():
        return "start"

    @task
    def read_limit(value: str, limit: int) -> int:
        return limit

    child = Workflow(
        "narrow_policy",
        policy=WorkflowPolicy(max_parallel_tasks=1),
        start=Node(
            run=read_limit,
            bind_input=Binder[read_limit](limit=Policy.max_parallel_tasks),
        ),
    )

    run = await Workflow(
        "parent",
        policy=WorkflowPolicy(max_parallel_tasks=3),
        start=Node(run=load, next="child"),
        child=Node(run=child),
    ).run()

    assert run.result == 1
    assert run.outputs == {
        branch_id[0]: {
            "load": ["start"],
            "narrow_policy": [1],
        }
    }


@pytest.mark.asyncio
async def test_child_workflow_cannot_widen_parent_policy():
    @task
    def load():
        return "start"

    @task
    def identity(value: str) -> str:
        return value

    child = Workflow(
        "widen_policy",
        policy=WorkflowPolicy(max_parallel_tasks=3),
        start=identity,
    )
    parent = Workflow(
        "parent",
        policy=WorkflowPolicy(max_parallel_tasks=1),
        start=Node(run=load, next="child"),
        child=Node(run=child),
    )

    with pytest.raises(TypeError, match="policy is not allowed by inherited policy"):
        await parent.run()


@pytest.mark.asyncio
async def test_child_workflow_can_disable_parent_runtime_expansion_policy(branch_id):
    @task
    def load():
        return "start"

    @task
    def read_flag(value: str, allowed: bool) -> bool:
        return allowed

    child = Workflow(
        "narrow_expansion",
        policy=WorkflowPolicy(allow_runtime_expansion=False),
        start=Node(
            run=read_flag,
            bind_input=Binder[read_flag](allowed=Policy.allow_runtime_expansion),
        ),
    )

    run = await Workflow(
        "parent",
        policy=WorkflowPolicy(allow_runtime_expansion=True),
        start=Node(run=load, next="child"),
        child=Node(run=child),
    ).run()

    assert run.result is False
    assert run.outputs == {
        branch_id[0]: {
            "load": ["start"],
            "narrow_expansion": [False],
        }
    }


@pytest.mark.asyncio
async def test_child_workflow_cannot_enable_parent_runtime_expansion_policy():
    @task
    def load():
        return "start"

    @task
    def identity(value: str) -> str:
        return value

    child = Workflow(
        "widen_expansion",
        policy=WorkflowPolicy(allow_runtime_expansion=True),
        start=identity,
    )
    parent = Workflow(
        "parent",
        policy=WorkflowPolicy(allow_runtime_expansion=False),
        start=Node(run=load, next="child"),
        child=Node(run=child),
    )

    with pytest.raises(TypeError, match="policy is not allowed by inherited policy"):
        await parent.run()


@pytest.mark.asyncio
async def test_workflow_policy_rejects_static_cycles_by_default():
    @task
    def load():
        return "start"

    @task
    def identity(value: str) -> str:
        return value

    workflow = Workflow(
        "static_cycle",
        start=Node(run=load, next="one"),
        one=Node(run=identity, next="two"),
        two=Node(run=identity, next="one"),
    )

    with pytest.raises(TypeError, match="static cycle"):
        await workflow.run()


@pytest.mark.asyncio
async def test_workflow_policy_can_allow_static_cycles_in_graph(branch_id):
    @task
    def load():
        return "start"

    @task
    def identity(value: str) -> str:
        return value

    run = await Workflow(
        "allowed_static_cycle",
        policy=WorkflowPolicy(allow_cycles=True),
        start=load,
        one=Node(run=identity, next="two"),
        two=Node(run=identity, next="one"),
    ).run()

    assert run.result == "start"
    assert run.outputs == {
        branch_id[0]: {
            "load": ["start"],
        }
    }


class FileAccessPolicy(WorkflowPolicy):
    readable_paths: set[str] = Field(default_factory=set)
    writable_paths: set[str] = Field(default_factory=set)

    def allows(self, child: WorkflowPolicy) -> bool:
        return (
            isinstance(child, FileAccessPolicy)
            and super().allows(child)
            and child.readable_paths <= self.readable_paths
            and child.writable_paths <= self.writable_paths
        )


@pytest.mark.asyncio
async def test_custom_policy_can_define_domain_narrowing_rules(branch_id):
    @task
    def load():
        return "start"

    @task
    def count_readable(value: str, readable: set[str]) -> int:
        return len(readable)

    child = Workflow(
        "read_only_child",
        policy=FileAccessPolicy(
            readable_paths={"/workspace/report.md"},
            writable_paths=set(),
        ),
        start=Node(
            run=count_readable,
            bind_input=Binder[count_readable](readable=Policy.readable_paths),
        ),
    )

    run = await Workflow(
        "parent",
        policy=FileAccessPolicy(
            readable_paths={"/workspace/report.md", "/workspace/data.csv"},
            writable_paths={"/workspace/report.md"},
        ),
        start=Node(run=load, next="child"),
        child=Node(run=child),
    ).run()

    assert run.result == 1
    assert run.outputs == {
        branch_id[0]: {
            "load": ["start"],
            "read_only_child": [1],
        }
    }


@pytest.mark.asyncio
async def test_custom_policy_rejects_domain_widening():
    @task
    def load():
        return "start"

    @task
    def identity(value: str) -> str:
        return value

    child = Workflow(
        "wider_file_child",
        policy=FileAccessPolicy(
            readable_paths={"/workspace/report.md", "/etc/passwd"},
        ),
        start=identity,
    )
    parent = Workflow(
        "parent",
        policy=FileAccessPolicy(
            readable_paths={"/workspace/report.md"},
        ),
        start=Node(run=load, next="child"),
        child=Node(run=child),
    )

    with pytest.raises(TypeError, match="policy is not allowed by inherited policy"):
        await parent.run()
