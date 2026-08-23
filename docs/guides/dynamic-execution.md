# Dynamic Execution

!!! warning "Capability status"
    Yield-driven multiplicity is **Available**. Runtime `Expand` / `Fragment`
    materialization is **Experimental**. Expansion budgets, serialized final
    graphs, and declaration-only graph inspection are **Planned**. See the
    [canonical status ledger](../status.md).

This guide covers yield-driven runtime multiplicity and explicit graph growth
through `Expand` and `Fragment`.

## Current state

Yield-based fan-out is available today. A sync or async generator task may yield
multiple values, and each yielded value is routed independently through the
node's `next` value.

```python
from elan import Join, Node, Workflow, task


@task
def load_items():
    yield 1
    yield 2
    yield 3


@task
def double(item: int) -> int:
    return item * 2


@task
def total(values: list[int]) -> int:
    return sum(values)


workflow = Workflow(
    "double_items",
    start=Node(run=load_items, next="double"),
    double=Node(run=double, next="result"),
    result=Join(run=total),
)
```

The generator task is recorded once in `WorkflowRun.outputs` with the collected
yielded items. Downstream branches are scheduled per item and may run before the
generator has finished.

## Runtime expansion

Use `Expand(builder)` as a node's complete `next` value when the emitted packet
determines which graph structure should run next. The builder is synchronous
orchestration code, not a `Task`. It receives the packet after `bind_output` and
returns one self-routed `Fragment`.

Because this surface is Experimental, applications should isolate expansion
builders and avoid treating generated node identifiers as a stable external API.

```python
from pydantic import BaseModel

from elan import Expand, Fragment, Node, Workflow, WorkflowPolicy, task


class Plan(BaseModel):
    value: int


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
def publish(value: int) -> str:
    return f"value={value}"


@task
def finish(value: str) -> str:
    return value


def build(plan: Plan) -> Fragment:
    return Fragment(
        start=Node(run=prepare, next="process"),
        process=Node(run=process, next="publish"),
    )


workflow = Workflow(
    "dynamic",
    policy=WorkflowPolicy(allow_runtime_expansion=True),
    start=Node(run=create_plan, next=Expand(build)),
    publish=Node(run=publish, next="result"),
    result=finish,
)
```

A fragment has its own executable `start` and local node names, but no workflow
name, context, policy, or result boundary. Local routes resolve before enclosing
fragment routes and static workflow routes. A local declaration named `result`
is rejected, so `next="result"` always refers to the workflow terminal.

Before scheduling the fragment entry, Elan gives every invocation a run-local
namespace and validates the complete candidate graph. Task and target
resolution, routing forms, scoped joins, nested `Expand` sites, result
terminality, and cycle policy must all be valid. A rejected candidate schedules
none of its tasks and does not modify the live run graph.

Fragments may define activation-scoped joins, contain nested expansion sites,
or route to enclosing/static nodes and joins. Generator yields materialize an
isolated fragment invocation per yielded packet. Expanded work inherits the
current context, policy, and active join memberships.

There is deliberately no expansion-depth or total-materialization limit when
`allow_runtime_expansion=True`. Recursive builders must therefore provide their
own terminating condition. Static cycles still require `allow_cycles=True`.

## Deferred surface

Callable `next` and `then`/`finally`-style expansion continuations are deferred.
Graph serialization, final-graph introspection on `WorkflowRun`, cross-edge type
analysis, reachability analysis, and expansion budgets are also outside this
initial slice.

## Related guides

See:

- [Branching](branching.md)
- [Runtime Behavior](../reference/runtime-behavior.md)
- [Adaptive Research](adaptive-research.md)
- [Document Decisioning](document-decisioning.md)
- [AI-assisted ETL Recovery](etl-recovery.md)
