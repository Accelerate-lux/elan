# Quickstart

This is the fastest path from zero to a working Elan workflow.

Use this page when you want the smallest runnable example before reading about the broader model.

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

print(run.result)
# Hello, World!

print(run.outputs)
# {
#     "branch-1": {
#         "prepare": ["World"],
#         "greet": ["Hello, World!"],
#     }
# }
```

What this example shows:

- tasks are plain Python functions decorated with `@task`
- `Workflow` defines the graph
- `Node` attaches routing information to a task
- `run.result` returns the exported workflow value
- `run.outputs` records executed task outputs grouped by branch id

Next:

- [Core Concepts](core-concepts.md)
- [Linear Workflows](../guides/linear-workflows.md)
- [Data Binding](../guides/data-binding.md)
