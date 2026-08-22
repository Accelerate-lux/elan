# Runtime Behavior

This page captures the exact public runtime semantics that matter when reading Elan workflow results.

## `WorkflowRun.result`

- if the workflow defines a reserved `result` node, `WorkflowRun.result` is that node's raw return; `bind_output` does not alter the exported result
- if the workflow defines `result=Join(...)`, `WorkflowRun.result` is the finalized join value
- if no reserved `result` is defined and the workflow is linear, `WorkflowRun.result` falls back to the last terminal output
- if the workflow uses branching forms and does not define reserved `result`, `WorkflowRun.result` is `None`
- a reserved result join is enforced as terminal

Known specification gap: an ordinary reserved result node may currently declare
`next`; execution continues while the recorded result remains unchanged. The
accepted contract requires every reserved result form to be terminal and the
workflow constructor to reject this declaration.

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

When a join has a reducer, its raw return is recorded under the reducer task name
on the join owner branch. Reducer-less joins do not add an output entry.

## Binding behavior

Between nodes, Elan currently binds values using these rules:

- scalar outputs may bind to one downstream parameter
- tuple outputs may bind positionally to a fixed downstream signature
- list outputs remain opaque values
- raw `dict` outputs remain opaque values
- Pydantic model outputs may pass through as one value or auto-unpack by field name
- `Node.bind_output` may create a named adapter payload
- `Node.bind_input` may be a raw dictionary or `Binder[task]`
- `Node.bind_input` may provide literal values or read from `Upstream.field`, `Input.field`, `Context.field`, and `Policy.field`
- generator task outputs are collected as one list in `WorkflowRun.outputs`; each yielded item is routed independently
- `Node(run=child_workflow)` records the child workflow result once in the parent outputs

## Policy behavior

Current policy semantics:

- workflow policy is declared as a `WorkflowPolicy` instance on `Workflow(..., policy=...)`
- if no policy is declared, the run uses the base `WorkflowPolicy`
- policy is immutable for a run
- child workflows inherit the parent policy
- child workflows may refine policy if `parent_policy.allows(child_policy)` returns `True`
- `max_parallel_tasks` limits concurrently running activations in one workflow run
- `allow_cycles=False` rejects static cycles in the declared graph
- `allow_runtime_expansion` is a governance flag for future runtime expansion features

## Context behavior

Current context semantics:

- workflow context is declared as a Pydantic model class on `Workflow(..., context=...)`
- each workflow run starts with a fresh instance of that model
- `Workflow.bind_context` may be a raw dictionary or `Binder[ContextModel]`
- `Node.context` may be a raw dictionary or `Binder[ContextModel]`
- context is branch-local, not one shared mutable object for the whole run
- child branches inherit the parent branch context at branch creation time
- child workflows inherit a copy of the current branch context
- successful child workflows commit their final context before the parent continues
- sibling branches do not observe each other's later context writes

## Composition behavior

Current composition semantics:

- a parent node may run a child workflow with `Node(run=child_workflow)`
- the parent receives the child workflow's exported `WorkflowRun.result`
- child internal outputs are not merged into parent `WorkflowRun.outputs`
- parent `Node.bind_input` may adapt the packet before the child starts
- a child workflow with a declared context model must match the inherited context model
- child workflows inherit parent policy and may only narrow it

Current write phases:

- `Node.context` runs before task execution
- `Node.context` may read the previous node's emitted value through `Upstream.field` on non-entry nodes

Current supported context sources are intentionally narrow:

- literals
- `Input.field`
- `Context.field`
- `Policy.field`
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

`Join` semantics:

- `result=Join()` without `scope` waits for workflow-wide quiescence
- a scoped join creates one barrier per activation of its declared scope node
- all descendant branches are awaited, including branches that do not contribute
- branches routed to the join contribute their emitted values
- `Join()` returns the collected list
- `Join(run=reducer)` calls the reducer with the collected list as one value
- a scoped reducer runs on the preserved scope-owner branch and may receive its context
- mid-graph joins route their reduced value through `bind_output`, `route_on`, and `next`
- reducer returns are recorded in `WorkflowRun.outputs`; reducer-less joins add no entry
- distinct scoped joins may nest; the inner reducer and continuation remain outer-scope work
- concurrent activations of a mid-graph scope reduce independently
- terminal scoped joins require exactly one scope activation
- sibling branch contexts are never merged implicitly

## Concurrency behavior

Sibling runnable branches execute concurrently.

Current scheduler behavior:

- runnable activations are launched up to `WorkflowPolicy.max_parallel_tasks`
- concurrency is unlimited when `max_parallel_tasks` is `None`
- join contribution order follows runtime arrival order
- reducers should therefore be order-agnostic unless the workflow explicitly constrains completion order
