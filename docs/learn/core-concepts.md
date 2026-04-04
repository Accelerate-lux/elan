# Core Concepts

Elan separates business logic from orchestration by using three main concepts:

- **Task**: the unit of work
- **Node**: the routing wrapper around a task
- **Workflow**: the reusable graph definition

Executing a workflow produces a **WorkflowRun**, which contains:

- `result`: the exported workflow value
- `outputs`: the execution log grouped by branch id and task name

## Tasks

A task is a standard Python function, synchronous or asynchronous, registered with `@task`.

```python
from elan import task


@task
async def hello():
    return "Hello, world!"
```

Tasks stay independent from routing and orchestration logic.

## Nodes

A `Node` places a task inside the graph and can define:

- `run`
- `next`
- `bind_input`
- `bind_output`
- `route_on`

If a task is the only step or final step in a workflow, it can often be used directly. As soon as routing matters, wrap it in a `Node`.

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

## Workflow Runs

Calling `await workflow.run(...)` executes the graph and returns a `WorkflowRun`.

For a single-task workflow:

```python
{
    "branch-1": {
        "hello": ["Hello, world!"],
    }
}
```

If the workflow defines a reserved `result`, `WorkflowRun.result` exposes that exported value. Otherwise it falls back to the last terminal output for linear workflows.

## Task Identity

Tasks can be referenced in workflows:

- directly by `Task`
- by canonical registry key
- by explicit alias

The `run` field resolves task references from the task registry. The `next` field always refers to workflow-local node names.

Next:

- [Linear Workflows](../guides/linear-workflows.md)
- [Data Binding](../guides/data-binding.md)
- [Branching](../guides/branching.md)
