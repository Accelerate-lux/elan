# Elan

![Elan](elan-pic.webp)

Elan is a graph-native orchestration engine for dynamic agent and data workflows.

While traditional DAG-based orchestrators excel at static scheduling, they struggle when a workflow's structure isn't fully known ahead of time. Conversely, many agent frameworks offer dynamic execution but introduce heavy boilerplate, rigid patterns, and unpredictable behaviors. 

Designed with developer experience in mind, Elan bridges this gap by offering a simple, predictable orchestration model:

- **Dynamic Execution:** A core model where branches can expand, recurse, and synchronize at runtime as your workflow emerges.
- **Unified Execution Model:** Write workflows in pure Python, YAML/JSON config, or HTTP API payloads—all share the exact same orchestration model and semantics.
- **Simple Mental Model:** A declarative API that strictly separates pure business logic (Tasks) from routing and orchestration (Workflows).
- **Intuitive Graph Control:** Branching, fan-out, and conditional routing are declared explicitly at the workflow level. You maintain full control over the graph's behavior without hiding routing logic inside your tasks.
- **Native Cycles:** Unlike traditional DAGs, cycles are a first-class concept. Loops and recursive agent patterns are just natural cycles in the graph, requiring no special syntax or workarounds.
- **Type-Safe Data Flow:** Built around standard Python type hints and Pydantic models. It automatically binds data for simple cases and provides explicit adapters to reshape inputs and outputs.
- **Static and Runtime Graph Validation:** Ensures graph integrity through static validation before execution, and applies semi-static runtime validation as dynamic structures materialize.
- **First-Class Composability:** Sub-workflows compose cleanly as standard nodes. Build complex graphs by nesting smaller, reusable workflows with explicit `result` boundaries.
- **Testable by Design:** Because tasks are just plain Python functions that know nothing about the graph, you can unit test your business logic without mocking the orchestrator.
- **Workload & Framework Agnostic:** Whether you are coordinating standard Python data tasks or complex agent loops, Elan provides a consistent interface that doesn't lock you into a proprietary LLM ecosystem.

The name—pronounced "ay-lan"—comes from the French word "élan" which mean both momentum and moose.

## Why Elan?

Building data pipelines and AI agents usually means stitching together different tools: static DAGs for data, and specialized state-machine runtimes for agents. This leads to a patchwork of frameworks and disjointed developer experiences.

Elan is a multi-purpose orchestrator designed to handle both. Built with developer experience and flexibility at its core, it is easy to get started with for simple tasks, yet powerful enough for complex dynamic use cases without introducing heavy boilerplate. This means you no longer need to learn and maintain entirely different tools for your data pipelines and your AI agents.

- **One Tool for Data and Agents:** Whether you are orchestrating standard data workflows or complex, recursive agent loops, Elan provides the exact same predictable, graph-native interface.
- **Runtime Graph Materialization:** Unlike tools that just do dynamic mapping or traverse a pre-compiled state graph, Elan can materialize entirely new workflow structures into the active graph at runtime.
- **Strict Task/Orchestration Separation:** Tasks are pure Python functions. Routing is declared explicitly at the workflow level, making it easy to test your business logic and compose smaller workflows together.

| Capability | Traditional DAGs | Agent Runtimes | Elan |
| :--- | :--- | :--- | :--- |
| **Runtime Multiplicity** | Strong | Strong | **Native** |
| **Runtime Control Flow** | Weak / Moderate | Strong | **Native** |
| **Runtime Graph Materialization** | N/A | Weak | **Native** |
| **Explicit Routing** | Moderate | Strong | **Native** |
| **Composition** | Moderate | Moderate | **Native** |

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
# Hello, World!

print(run.outputs)
# {'prepare': ['World'], 'greet': ['Hello, World!']}
```

## Documentation

For a complete introduction to Elan's mental model, graph topology, and data binding rules, read the [Basics Guide](docs/basics.md).

For side-by-side assessments of tools adjacent to Elan, read the [Comparison Summary](docs/comparison/summary.md) and the focused note on [what "dynamic" means across workflow tools](docs/comparison/dynamic_models.md).

For rough candidate demos and later-planning notes, read the [Demo Ideas Catalog](docs/demo_ideas_catalog.md).
