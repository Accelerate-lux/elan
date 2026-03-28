# Elan

![Elan](elan-pic.webp)

Elan is a graph-native orchestration engine for dynamic agent and data workflows.

While traditional DAG-based orchestrators excel at static scheduling, they struggle when a workflow's structure isn't fully known ahead of time. Conversely, many agent frameworks offer dynamic execution but introduce heavy boilerplate, rigid patterns, and unpredictable behaviors. 

Designed with developer experience in mind, Elan bridges this gap by offering a simple, predictable orchestration model:

- **Dynamic Execution:** A core model where branches can expand, recurse, and synchronize at runtime as your workflow emerges.
- **Simple Mental Model:** A declarative API that strictly separates pure business logic (Tasks) from routing and orchestration (Workflows).
- **Native Pydantic Integration:** Built around standard Python type hints and Pydantic models. This gives your IDE maximum context and automatically validates data as it flows between nodes.
- **Framework Agnostic:** Elan doesn't lock you into a proprietary LLM ecosystem. Because tasks are just Python functions, you can easily orchestrate any model, API, or custom logic without fighting the framework.
- **Testable by Design:** Because tasks are just plain Python functions that know nothing about the graph, you can unit test your business logic without mocking the orchestrator.
- **Workload Agnostic:** Whether you are coordinating standard Python data tasks or complex agent loops, Elan provides a consistent interface.
- **Easily Extensible:** The core architecture is built around standard Python primitives, making it trivial to write custom adapters, integrate third-party tools, or extend the orchestrator's capabilities to fit your specific needs.
- **Low Boilerplate:** Designed to get out of your way, it is simple to learn and easily moves from local setup to production without over-engineering your codebase.

The name—pronounced "ay-lan"—comes from the French word "élan" which mean both momentum and moose.

## Quickstart

Elan separates the work you want to do (Tasks) from how that work is routed (Nodes) and orchestrated (Workflows).

Here is how you define a simple linear workflow where the output of one task automatically flows into the next:

```python
import asyncio
from elan import Node, Workflow, task

# 1. Define your pure business logic as tasks
@task
def prepare():
    return "World"

@task
async def greet(name: str):
    return f"Hello, {name}!"

# 2. Orchestrate them into a workflow graph
workflow = Workflow(
    "greet_world",
    # Wrap tasks in Nodes to define routing edges
    start=Node(run=prepare, next="greet"),
    greet=greet,
)

# 3. Execute the graph
run = asyncio.run(workflow.run())

print(run.result)
# {'prepare': ['World'], 'greet': ['Hello, World!']}
```

## Documentation

For a complete introduction to Elan's mental model, graph topology, and data binding rules, read the [Basics Guide](docs/basics.md).
