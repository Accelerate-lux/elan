# Next Steps

You now have the basic onboarding model:

- tasks hold business logic
- nodes hold orchestration choices
- workflows define the graph
- workflow runs expose `result` and `outputs`

The next step depends on what you want to learn next.

## If you want more linear examples

Read [Linear Workflows](../guides/linear-workflows.md).

This is the next step if you want to get comfortable with the basic graph shape before adding branching.

## If you want to understand how values move

Read [Data Binding](../guides/data-binding.md).

This is the next step if you want to understand:

- default downstream binding
- `bind_input`
- `bind_output`
- structured payloads

## If you want to branch or fan out

Read [Branching](../guides/branching.md).

This is the next step if you want to understand:

- `next=[...]`
- `next={...}` with `route_on`
- `When(...)`

## If you need multiple branches to converge

Read [Join on Result](../guides/join-result.md).

This is the next step if multiple branches must contribute to one final output.

## If you want exact runtime semantics

Read [Runtime Behavior](../reference/runtime-behavior.md).

This is the next step if you need precise rules for:

- `WorkflowRun.result`
- branch-aware `outputs`
- join ordering
- concurrent sibling execution
