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
    "branch-<uuid>": {
        "prepare": ["world"],
        "greet": ["Hello, world!"],
    }
}
```

Branched example:

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
- generator task outputs are collected as one list in `WorkflowRun.outputs`; each yielded item is routed independently

## Context behavior

Current context semantics:

- workflow context is declared as a Pydantic model class on `Workflow(..., context=...)`
- each workflow run starts with a fresh instance of that model
- context is branch-local, not one shared mutable object for the whole run
- child branches inherit the parent branch context at branch creation time
- sibling branches do not observe each other's later context writes

Current write phases:

- `Node.context` runs before task execution
- `Node.context` may read the previous node's emitted value through `Upstream.field` on non-entry nodes

Current supported context sources are intentionally narrow:

- literals
- `Input.field`
- `Context.field`
- `Upstream.field` for non-entry nodes

Context updates are partial merges into the current branch scope. Unknown fields and invalid values fail clearly.

## Branching behavior

Current supported routing forms:

- exclusive branching with `next={...}` and `route_on`
- fan-out with `next=[...]`
- yield-based fan-out from sync and async generator tasks
- conditional multi-routing with `When(...)`
- mixed `next=[str | When, ...]` target-producer lists

For yield-based fan-out, every yielded item is treated like one node output packet:

- `Node.bind_output` is applied per yielded item
- `next`, `When(...)`, and `route_on` are resolved per yielded item
- downstream branches may start before the generator task has finished
- the generator activation completes only after the generator is exhausted
- yielding into reserved `result=Node(...)` is unsupported; use `result=Join(...)`

Ref-based `route_on` currently applies to exclusive branching only.

## Join behavior

Current `Join` semantics:

- terminal-only on reserved `result`
- branches routed to `result` contribute their emitted values
- `Join()` returns the collected list
- `Join(run=reducer)` calls the reducer with the collected list as one value
- `Join(...)` does not merge branch-local context in the current runtime

## Concurrency behavior

Sibling runnable branches execute concurrently.

Current scheduler behavior:

- all runnable activations are launched
- concurrency is currently unlimited
- join contribution order follows runtime arrival order
- reducers should therefore be order-agnostic unless the workflow explicitly constrains completion order
