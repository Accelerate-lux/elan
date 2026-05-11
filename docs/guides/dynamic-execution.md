# Dynamic Execution

This guide covers the dynamic execution features available today and the runtime
graph growth features planned later.

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

Dynamic expansion and callable runtime continuation are not implemented yet.

## Planned coverage

This page will eventually document:

- `Expand(...)`
- callable `next`
- append-only graph growth
- cycles and guardrails

## For now

See:

- [Branching](branching.md)
- [Runtime Behavior](../reference/runtime-behavior.md)
