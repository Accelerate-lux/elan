# Recommended Patterns

This page answers a practical onboarding question: when Elan gives you more than one valid form, which one should you choose first?

The goal is not to hide alternatives. The goal is to give you a strong default path.

## Task vs `Node`

### Recommended

Use plain `@task` functions for business logic and wrap them in `Node(...)` once routing or binding matters.

Use this when:

- a task routes to another node
- a task needs `bind_input` or `bind_output`
- a task participates in branching

### Alternative

Use a bare task directly for:

- a trivial single-step workflow
- a final step with no routing configuration

### Why this is the default

`Node(...)` makes orchestration visible without polluting the task itself.

## Plain Pydantic model vs `@ref`

### Recommended

Use plain Pydantic models first for structured payloads.

Use this when:

- you want one task to emit structured data
- the downstream task expects the model directly
- the downstream task can bind matching fields by name

### Alternative

Use `@ref` only when you need field-reference features such as:

- `Upstream.field`
- `Context.field`
- ref-based `route_on`
- `When(Model.field, ...)`

### Why this is the default

Ordinary structured-data binding does not require `@ref`, so keeping models plain avoids extra ceremony.

## `next="node"` vs branching forms

### Recommended

Start with `next="node"` for simple continuation.

Use this when:

- one step leads to one next step
- you are learning the graph model
- branching is not required yet

### Alternatives

- use `next=[...]` for fan-out
- use `next={...}` with `route_on` for value-based exclusive routing
- use `When(...)` for condition-based routing

### Why this is the default

Single-target routing is the smallest unit of workflow structure. It makes the graph easy to read before you introduce routing choices.

## `next=[...]` vs `next={...}` vs `When(...)`

### Recommended

Choose the branching form based on the kind of decision you are making:

- use `next=[...]` when the output should go to multiple places
- use `next={...}` with `route_on` when one value selects one path
- use `When(...)` when targets are enabled by boolean conditions

### Why this is the default

Elan has multiple routing forms because fan-out, value dispatch, and conditional routing are different workflow shapes. Keeping them separate makes each one easier to read.

## Default binding vs explicit binding

### Recommended

Rely on default binding first.

Use this when:

- one scalar moves into one parameter
- a tuple matches a fixed downstream signature
- a Pydantic model should pass through directly or bind by matching field name

### Alternative

Use `bind_output` or `bind_input` when the shape must be made explicit.

### Why this is the default

Default binding keeps small workflows short. Explicit binding becomes valuable when the data shape stops being obvious.

## `result=Node(...)` vs `result=Join(...)`

### Recommended

Use a simple reserved `result` node, or rely on the terminal linear result, when one path produces the final output.

Use this when:

- the workflow is linear
- one final step defines the exported result

### Alternative

Use `result=Join(...)` when multiple branches must contribute to one final result.

### Why this is not the default

`Join` is a synchronization tool. Most first workflows do not need that complexity.

What you understand now:

- which forms to choose first
- when to keep things implicit
- when to reach for branching, refs, and joins

Next:

- [Linear Workflows](../guides/linear-workflows.md) for more flow patterns
- [Data Binding](../guides/data-binding.md) for value movement
- [Branching](../guides/branching.md) for routing forms
