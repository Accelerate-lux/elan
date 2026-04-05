# Elan

Elan is a Python workflow orchestration engine for AI agents, data orchestration, and mixed workloads. It gives teams a unified tool to build complex multi-step systems, from data pipelines to agent-driven applications, that stay explicit, composable, and predictable as they grow.

Elan separates tasks from orchestration. Tasks stay plain Python, while routing, branching, joins, and workflow structure are defined explicitly in the workflow layer.

It supports fine-grained routing, branching, synchronization, and dynamic execution within the same programming model.

## Highlights

- **Dynamic Execution:** A core model where branches can expand, recurse, and synchronize at runtime as your workflow emerges.
- **Unified Execution Model:** Write workflows in pure Python, YAML/JSON config, or HTTP API payloads. They share the same orchestration model and semantics.
- **Simple Mental Model:** A declarative API that strictly separates pure business logic (Tasks) from routing and orchestration (Workflows).
- **Intuitive Graph Control:** Branching, fan-out, and conditional routing are declared explicitly at the workflow level.
- **DAG Opt-In:** Use DAG-shaped workflows when they fit, without making DAG constraints the center of the model.
- **Native Cycles:** Loops and recursive agent patterns fit the graph model naturally.
- **Type-Safe Data Flow:** Standard Python type hints and Pydantic models support automatic binding for simple cases and explicit adapters for reshaping inputs and outputs.
- **Static and Runtime Graph Validation:** Graph integrity is checked before execution and validated again as dynamic structures materialize.
- **First-Class Composability:** Smaller workflows compose cleanly into larger ones with explicit `result` boundaries.
- **Testable by Design:** Tasks remain plain Python functions that can be tested without mocking the orchestrator.
- **Workload Agnostic:** The same orchestration model works across data workflows, agent workflows, and mixed systems.

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
