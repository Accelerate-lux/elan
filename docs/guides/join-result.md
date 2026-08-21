# Joins

Elan supports workflow-wide terminal joins and activation-scoped mid-graph joins.

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

## Workflow-wide semantics

- branches routed to `result` contribute their emitted values
- `Join()` returns the collected list
- `Join(run=reducer)` calls the reducer with that list as one value
- reducer results are recorded in `run.outputs` under the reducer task name

## Scoped mid-graph join

Use `scope` to identify the activation whose descendants form the barrier:

```python
workflow = Workflow(
    "review",
    start=Node(run=prepare, next=["identity", "budget"]),
    identity=Node(run=check_identity, next="checks"),
    budget=Node(run=check_budget, next="checks"),
    checks=Join(
        run=merge_checks,
        scope="start",
        route_on="route",
        next={"continue": "publish", "stop": "reject"},
    ),
    publish=publish,
    reject=reject,
)
```

Every activation of `start` creates a separate join instance. All descendants are
awaited, while only descendants routed to `checks` contribute. The reducer runs
on the preserved `start` branch, so context changes made there are visible to the
selected continuation.

Scoped joins can nest. An inner reducer and its continuation remain pending work
for the enclosing scope. Concurrent activations of the same mid-graph scope remain
isolated from one another.

## Ordering caveat

Join contribution order follows runtime arrival order.

That means reducers should be order-agnostic unless the workflow intentionally constrains completion timing.

## Limits

- a mid-graph join requires an explicit scope
- one scope node may define only one join boundary
- the same join scope cannot recursively re-enter on one branch
- a terminal scoped join requires exactly one activation

## Next steps

- [Runtime Behavior](../reference/runtime-behavior.md)
