# Core Concepts

Elan separates business logic from orchestration by using four main concepts:

- **Task**: the unit of work
- **Node**: the routing wrapper around a task
- **Workflow**: the reusable graph definition
- **WorkflowRun**: the result of executing one workflow instance

This page is the durable mental model for those objects. Use it after the first walkthrough, then come back to it as the guides get more specific.

## Tasks

A task is a standard Python function, synchronous or asynchronous, registered with `@task`.

```python
from elan import task


@task
async def hello():
    return "Hello, world!"
```

Tasks stay independent from routing and orchestration logic.

!!! note "Recommended"
    Keep business logic in tasks and keep routing decisions in the workflow definition. That separation is one of the main reasons to use Elan.

## Nodes

A `Node` places a task inside the graph and can define:

- `run`
- `next`
- `bind_input`
- `bind_output`
- `route_on`

If a task is the only step or final step in a workflow, it can often be used directly. As soon as routing matters, wrap it in a `Node`.

!!! note "Recommended"
    Treat `Node(...)` as the default workflow form once a task needs routing or data adaptation.

!!! note "Alternative"
    Using a bare task directly in `start=` or as a downstream node is fine for the smallest workflows, but it is not the best default once the graph becomes more explicit.

## Workflows

A `Workflow` is a reusable graph blueprint. It defines:

- the `start` node
- named downstream nodes
- optional reserved `result`
- optional workflow context model

```python
from elan import Workflow, task


@task
async def hello():
    return "Hello, world!"


workflow = Workflow("hello_world", start=hello)
```

A workflow is the orchestration layer. It connects tasks, names nodes, and defines how values move between steps.

## Workflow Runs

Calling `await workflow.run(...)` executes the graph and returns a `WorkflowRun`.

`WorkflowRun` exposes two public things that matter immediately:

- `result`: the exported workflow value
- `outputs`: the execution log grouped by branch id and task name

For a single-task workflow:

```python
{
    "branch-<uuid>": {
        "hello": ["Hello, world!"],
    }
}
```

If the workflow defines a reserved `result`, `WorkflowRun.result` exposes that exported value. Otherwise it falls back to the last terminal output for linear workflows.

If the workflow uses branching forms and does not define reserved `result`, `WorkflowRun.result` becomes `None`.

!!! note "Why `outputs` is branch-aware"
    Elan uses one output structure for both linear and branched runs. That keeps result inspection consistent as workflows grow from simple chains into richer routing patterns.

## Task Identity

Tasks can be referenced in workflows:

- directly by `Task`
- by canonical registry key
- by explicit alias

The `run` field resolves task references from the task registry. The `next` field always refers to workflow-local node names.

For onboarding, prefer direct task references first. Use string references when alias-based registration or configuration-driven workflow construction is important.

Next:

- [Recommended Patterns](recommended-patterns.md) for the preferred first-use forms
- [Linear Workflows](../guides/linear-workflows.md) for more examples
