# Runtime Behavior

This page captures the exact public runtime semantics that matter when reading Elan workflow results.

## `WorkflowRun.result`

- if the workflow defines a reserved `result` node, `WorkflowRun.result` is the exported value of that node
- if the workflow defines `result=Join(...)`, `WorkflowRun.result` is the finalized join value
- if no reserved `result` is defined and the workflow is linear, `WorkflowRun.result` falls back to the last terminal output
- if the workflow uses branching forms and does not define reserved `result`, `WorkflowRun.result` is `None`

## `WorkflowRun.outputs`

`WorkflowRun.outputs` stores executed task outputs grouped first by branch id, then by task name.

Linear example:

```python
{
    "branch-1": {
        "prepare": ["world"],
        "greet": ["Hello, world!"],
    }
}
```

Branched example:

```python
{
    "branch-1": {
        "prepare": ["world"],
    },
    "branch-2": {
        "greet": ["Hello, world!"],
    },
    "branch-3": {
        "badge": ["badge:world"],
    },
}
```

Join reduction itself is not recorded in `run.outputs`.

## Binding behavior

Between nodes, Elan currently binds values using these rules:

- scalar outputs may bind to one downstream parameter
- tuple outputs may bind positionally to a fixed downstream signature
- list outputs remain opaque values
- raw `dict` outputs remain opaque values
- Pydantic model outputs may pass through as one value or auto-unpack by field name
- `Node.bind_output` may create a named adapter payload
- `Node.bind_input` may provide literal values or read from `Upstream.field`, `Input.field`, and `Context.field`

## Branching behavior

Current supported routing forms:

- exclusive branching with `next={...}` and `route_on`
- fan-out with `next=[...]`
- conditional multi-routing with `When(...)`
- mixed `next=[str | When, ...]` target-producer lists

Ref-based `route_on` currently applies to exclusive branching only.

## Join behavior

Current `Join` semantics:

- terminal-only on reserved `result`
- branches routed to `result` contribute their emitted values
- `Join()` returns the collected list
- `Join(run=reducer)` calls the reducer with the collected list as one value

## Concurrency behavior

Sibling runnable branches execute concurrently.

Current scheduler behavior:

- all runnable activations are launched
- concurrency is currently unlimited
- join contribution order follows runtime arrival order
- reducers should therefore be order-agnostic unless the workflow explicitly constrains completion order
