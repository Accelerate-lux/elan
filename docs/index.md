# Elan

Elan is a graph-native orchestration engine for dynamic agent and data workflows.

Traditional DAG orchestrators are strong at static scheduling but awkward once the workflow structure needs to branch, synchronize, or grow at runtime. Many agent runtimes support dynamic control flow, but often with heavy framework ceremony or shared-state-machine abstractions. Elan is trying to sit between those two shapes.

## What Elan focuses on

- Dynamic execution where graph structure can branch, fan out, synchronize, and later expand at runtime
- A unified workflow model across Python code, config, and future API submissions
- Strict separation between pure task logic and orchestration/runtime logic
- Explicit routing rather than hidden control flow inside tasks
- A small interface that stays readable for simple workflows

## Quickstart

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

## Start here

- [Quickstart](learn/quickstart.md) for the smallest runnable example
- [Core Concepts](learn/core-concepts.md) for the Task / Node / Workflow model
- [Linear Workflows](guides/linear-workflows.md) and [Data Binding](guides/data-binding.md) for the first practical steps
- [Runtime Behavior](reference/runtime-behavior.md) for exact result, outputs, branching, and join semantics
- [Python Reference](reference/python-api.md) for generated API docs
- [Design Philosophy](design_philosophy.md) for the product direction

## Comparison notes

Elan is also documented against adjacent workflow tools to clarify what it means by dynamic execution and graph-native orchestration.

- [Comparison summary](comparison/summary.md)
- [Dynamic models taxonomy](comparison/dynamic_models.md)
