# Elan

![Elan](elan-pic.webp)

Elan is a graph-native orchestration engine for dynamic agent and data workflows.

While traditional DAG-based orchestrators excel at static scheduling, they struggle when a workflow's structure isn't fully known ahead of time. Conversely, many agent frameworks offer dynamic execution but introduce heavy boilerplate, rigid patterns, and unpredictable behaviors.

Designed with developer experience in mind, Elan bridges this gap by offering a simple, predictable orchestration model:

- **One Tool for Data and Agents:** Build data workflows, AI agents, and mixed systems in one orchestration model.
- **Plain Python, Reusable Tasks:** Keep business logic in plain Python functions that stay easy to reuse, test, and compose across workflows.
- **Fine-Grained Workflow Control:** Express fan-out, conditional routing, value-based branching, joins, and dynamic execution directly in the workflow.
- **Simple Mental Model:** Keep tasks and orchestration separate so workflow structure stays readable.
- **Unified Execution Model:** Write workflows in pure Python, YAML/JSON config, or HTTP API payloads while keeping one orchestration model and semantics.
- **Built for Mixed Workloads:** Use the same model for data workflows, AI agents, service orchestration, and human review steps.
- **First-Class Composability:** Compose smaller workflows into larger systems with explicit `result` boundaries.
- **Predictable Results:** Keep workflow outputs, result boundaries, and synchronization explicit.
- **DAG Opt-In:** Use DAG-shaped workflows when they fit, without making DAG constraints the center of the model.
- **Native Cycles:** Support loops and recursive agent patterns as part of the workflow model.
- **Type-Safe Data Flow:** Use Python type hints and Pydantic models for predictable data movement between steps.
- **Testable by Design:** Keep business logic easy to test in isolation.

## Implementation Status

| Feature area | Status |
| :--- | :--- |
| Basic workflows | ✅ Available |
| Data binding | ✅ Available |
| Structured payloads | ✅ Available |
| Branching and routing | ✅ Available |
| Workflow synchronization | ✅ Available |
| Concurrent execution | ✅ Available |
| Shared workflow context | ☐ Planned |
| Workflow composition | ☐ Planned |
| Dynamic graph expansion | ☐ Planned |

## Installation

```bash
pip install elan-workflow
```

The name, pronounced "ay-lan", comes from the French word "elan", which means both momentum and moose.

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

## Documentation

For a complete introduction to Elan's mental model, graph topology, and data binding rules, read the [Basics Guide](docs/basics.md).

For side-by-side assessments of tools adjacent to Elan, read the [Comparison Summary](docs/comparison/summary.md) and the focused note on [what "dynamic" means across workflow tools](docs/comparison/dynamic_models.md).

For rough candidate demos and later-planning notes, read the [Demo Ideas Catalog](docs/demo_ideas_catalog.md).
