# Quickstart

This is the fastest path from zero to a working Elan workflow.

Use this page when you want the smallest runnable example before reading about the broader model.

The goal here is not to show every feature. The goal is to get one small workflow running and make the main objects visible.

```python
import asyncio
from elan import Node, Workflow, task


@task
def prepare():
    return "World"


@task
async def greet(name: str):
    return f"Hello, {name}!"


workflow = Workflow(
    "greet_world",
    start=Node(run=prepare, next="greet"),
    greet=greet,
)

run = asyncio.run(workflow.run())
```

If you run that workflow:

```pycon
>>> run.result
'Hello, World!'
>>> run.outputs
{
    "branch-<uuid>": {
        "prepare": ["World"],
        "greet": ["Hello, World!"],
    }
}
```

What this example shows:

- tasks are plain Python functions decorated with `@task`
- `Workflow` defines the graph
- `Node` attaches routing information to a task
- `run.result` returns the exported workflow value
- `run.outputs` records executed task outputs grouped by branch id

!!! note "Recommended"
    Use `Node(...)` as soon as a task routes to another node or needs binding. It keeps the workflow shape explicit.

!!! note "Why `run.outputs` is grouped by branch id"
    Elan uses one branch-aware output shape for all runs, including linear ones. For a simple workflow you can usually treat the single branch as an execution log for the run.

What you understand now:

- how to register a task
- how to connect two steps into one workflow
- where to look for the final result
- where to inspect per-task outputs

Next:

- [Your First Workflow](your-first-workflow.md) for a line-by-line walkthrough of the same pattern
- [Core Concepts](core-concepts.md) for the durable mental model
