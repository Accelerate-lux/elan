# Join on Result

Elan currently supports a first-pass terminal join form on the reserved `result` node.

## Basic join

```python
from elan import Join, Node, Workflow, task


@task
def prepare():
    return "world"


@task
async def greet(name: str):
    return f"Hello, {name}!"


@task
async def badge(name: str):
    return f"badge:{name}"


@task
def collect(values: list[str]):
    return " | ".join(values)


workflow = Workflow(
    "fan_out_profile",
    start=Node(
        run=prepare,
        bind_output="name",
        next=["greet", "badge"],
    ),
    greet=Node(run=greet, next="result"),
    badge=Node(run=badge, next="result"),
    result=Join(run=collect),
)
```

## Current semantics

- `Join` is only valid as the reserved `result` node
- branches routed to `result` contribute their emitted values
- `Join()` returns the collected list
- `Join(run=reducer)` calls the reducer with that list as one value
- join reduction is not recorded in `run.outputs`

## Ordering caveat

Join contribution order follows runtime arrival order.

That means reducers should be order-agnostic unless the workflow intentionally constrains completion timing.

## Current limits

- no mid-graph joins yet
- no general barriers yet

## Next steps

- [Runtime Behavior](../reference/runtime-behavior.md)
- [Status](../explanations/status.md)
