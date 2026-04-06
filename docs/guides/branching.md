# Branching

This guide covers the currently supported routing forms in Elan.

## Exclusive branching

Use `next={...}` with `route_on` to choose one downstream node.

```python
workflow = Workflow(
    "branching_greet",
    start=Node(
        run=prepare,
        bind_output=["name", "style"],
        route_on="style",
        next={
            "formal": "greet_formal",
            "casual": "greet_casual",
        },
    ),
    greet_formal=greet_formal,
    greet_casual=greet_casual,
)
```

If the upstream value is a registered ref model, `route_on` may also use a ref field such as `RoutePayload.style`.

## Fan-out

Use `next=[...]` to route to multiple downstream nodes.

```python
workflow = Workflow(
    "fan_out_profile",
    start=Node(
        run=prepare,
        bind_output="name",
        next=["greet", "badge"],
    ),
    greet=greet,
    badge=badge,
)
```

## Conditional multi-routing

Use `When(...)` entries inside `next=[...]`:

```python
start=Node(
    run=classify,
    next=[
        When(RoutePayload.should_email, "send_email"),
        When(RoutePayload.should_ticket, ["open_ticket", "audit"]),
    ],
)
```

Lists are evaluated left to right as ordered target producers, so plain node ids and `When(...)` entries may be mixed.

## Branch-aware outputs

Branched workflows keep outputs separated by branch id:

```python
{
    "branch-<uuid-1>": {
        "prepare": ["world"],
    },
    "branch-<uuid-2>": {
        "greet": ["Hello, world!"],
    },
    "branch-<uuid-3>": {
        "badge": ["badge:world"],
    },
}
```

If a workflow uses branching forms and does not define reserved `result`, `run.result` is `None`.

## Current runtime notes

- sibling runnable branches execute concurrently
- scheduler concurrency is currently unlimited
- ordering between sibling branch completions is not guaranteed

## Next steps

- [Join on Result](join-result.md)
- [Runtime Behavior](../reference/runtime-behavior.md)
