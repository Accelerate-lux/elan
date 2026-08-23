# Recommended Patterns

!!! info "Capability status"
    These recommendations use the current **Available** API. Runtime expansion
    is **Experimental**; future authoring conveniences are listed separately on
    the [status page](../status.md).

This page answers a practical onboarding question: when Elan gives you more than one valid form, which one should you choose first?

The goal is not to hide alternatives. The goal is to give you a strong default path.

## Testable business logic today

### Recommended

When business logic must be invoked directly in unit tests, keep the raw typed
function and register it separately:

```python
from elan import task


def normalize_name(value: str) -> str:
    return value.strip().title()


normalize_name_task = task(normalize_name)

# Direct unit test of business logic; no workflow run is created.
assert normalize_name("  elan ") == "Elan"
```

Use `normalize_name_task` in workflow declarations and `normalize_name` in
ordinary unit tests. Direct invocation of the registered `Task` object itself
is **Planned**, not currently available.

### Why this is the default

It preserves a normal callable for isolated tests without reaching through
framework internals or misrepresenting a `Task` as directly callable.

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

## Workflow subclass vs constructor form

### Recommended

Use `class MyWorkflow(Workflow)` for application workflows.

Use this when:

- the workflow is part of the application codebase
- the graph has several named nodes
- the workflow benefits from forward-declared node references
- you want a stable file/module for documentation, review, and lint scoping

For larger workflows, prefer one workflow class per dedicated file. Put models,
tasks, and helper functions above the class or import them from adjacent modules.

### Alternative

Use `Workflow("name", start=..., **nodes)` for:

- tests
- short examples
- REPL exploration
- generated or programmatic graph construction

### Why this is the default

Subclass authoring matches normal Python expectations for application objects:
instantiating the class validates and builds a reusable workflow object, while
`run()` only executes it.

When an application workflow needs a typed public input surface, override
`run(...)` with a normal Python signature and delegate to `await self._run(...)`.

```python
class ReviewWorkflow(Workflow):
    start = Node(run=review)

    async def run(self, *, item_id: str, reviewer: str = "default"):
        return await self._run(item_id=item_id, reviewer=reviewer)
```

## Forward node references and Ruff

### Recommended

When subclass workflows use annotation-only forward declarations, put the
workflow in a dedicated module and use file-level Ruff `F821` suppression.

```python
# ruff: noqa: F821

class ReviewWorkflow(Workflow):
    review: Node
    result: Join

    start = Node(run=load_item, next=review)
    review = Node(run=review_item, next=result)
    result = Join(run=summarize)
```

Use this when:

- you want IDE navigation from `next=review` to the declared class member
- you want to avoid stringly typed edges in application workflow code
- the workflow lives in its own module

### Alternative

Use string node names, such as `next="review"`, when avoiding any lint
suppression matters more than IDE-connected node references.

If a workflow must live in a mixed module, use a narrower
`# ruff: disable[F821]` / `# ruff: enable[F821]` block around the wiring section
instead of suppressing the whole file.

### Why this is the default

The forward-reference names are valid at runtime because `Workflow` subclasses
provide a custom class namespace. Ruff cannot infer that metaclass behavior, so a
file-level suppression is clear when the module is dedicated to workflow
authoring, and it avoids adding `# noqa: F821` to every edge.

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

## Raw dict vs `Binder`

### Recommended

Use `Binder[...]` for explicit binding dictionaries in application
workflow code.

Use this when:

- `Workflow.bind_context` targets a context model with `Binder[ContextModel](...)`
- `Node.context` targets a context model with `Binder[ContextModel](...)`
- `Node.bind_input` targets a task with `Binder[some_task](...)`
- you want misspelled context fields or task parameters to fail when declared

### Alternative

Use a raw dictionary for compact examples, tests, and generated workflows.

### Why this is the default

`Binder` keeps the authoring surface explicit without changing runtime
semantics. It is still a dictionary, but it carries the intended binding target
and validates keys early.

## Domain config vs context vs policy

### Recommended

Keep domain configuration as ordinary user data.

Use Pydantic models and workflow input for application knobs such as:

- thresholds
- scoring weights
- feature flags
- business rules

Use `WorkflowPolicy` only for runtime governance, such as concurrency limits and
graph-shape permissions. Use workflow context for branch-local runtime state or
metadata that tasks should read through `Context.field`.

### Why this is the default

Domain configuration belongs to the application. Elan should not need a
framework-level concept for every kind of user setting, and context is clearest
when it is not overloaded with static business configuration.

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
