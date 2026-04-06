# Elan

Elan is a workflow orchestration engine for AI agents, data orchestration, and mixed workloads. It gives teams a unified tool to build complex multi-step systems, from data pipelines to agent-driven applications, that stay explicit, composable, and predictable as they grow.

Elan separates tasks from orchestration. Tasks stay plain Python, while routing, branching, joins, and workflow structure are defined explicitly in the workflow layer.

It supports fine-grained routing, branching, synchronization, and dynamic execution within the same programming model.

## Highlights

- **One Tool for Data and Agents:** Build data workflows, AI agents, and mixed systems in one orchestration model.
- **Plain Python, Reusable Tasks:** Keep business logic in plain Python functions that stay easy to reuse, test, and compose across workflows.
- **Fine-Grained Workflow Control:** Express fan-out, conditional routing, value-based branching, joins, and dynamic execution directly in the workflow.
- **Simple Mental Model:** Keep tasks and orchestration separate so workflow structure stays readable.
- **Unified Execution Model:** Use the same orchestration model across Python code, YAML/JSON config, and HTTP API payloads.
- **Built for Mixed Workloads:** Use the same model for data workflows, AI agents, service orchestration, and human review steps.
- **First-Class Composability:** Smaller workflows compose cleanly into larger ones with explicit `result` boundaries.
- **Predictable Results:** Keep workflow outputs, result boundaries, and synchronization explicit.
- **DAG Opt-In:** Use DAG-shaped workflows when they fit, without making DAG constraints the center of the model.
- **Native Cycles:** Support loops and recursive agent patterns as part of the workflow model.
- **Type-Safe Data Flow:** Use Python type hints and Pydantic models for predictable data movement between steps.
- **Testable by Design:** Keep business logic easy to test in isolation.

## Implementation Status


| Feature area             | Status         |
| ------------------------ | -------------- |
| Basic workflows          | ✅ Available   |
| Data binding             | ✅ Available   |
| Structured payloads      | ✅ Available   |
| Branching and routing    | ✅ Available   |
| Workflow synchronization | ✅ Available   |
| Concurrent execution     | ✅ Available   |
| Shared workflow context  | ☐ Planned      |
| Workflow composition     | ☐ Planned      |
| Dynamic graph expansion  | ☐ Planned      |


## Installation

```bash
pip install git+https://github.com/Accelerate-lux/elan.git
```

## Example

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

What happens in this example:

- The plain Python functions `prepare` and `greet` are decorated with `@task` to make them discoverable by Elan
- The `start=` keyword defines the workflow entrypoint, so Elan begins execution at `prepare`
- The `Workflow` object defines the execution graph and names the downstream `greet` node
- The `Node(run=prepare, next="greet")` declaration tells Elan to run `prepare` first and then route its output to `greet`
- For linear workflows with only one terminal step, the return value of the terminal node is automatically mapped into `run.result` 
- The `run.outputs` mapping records emitted values by branch id first and then by task name

!!! note "Terminal tasks"
    For terminal nodes, if you don't need to configure anything, passing the task directly is fine. Elan will automatically wrap it into a node.

## Start here

- [Getting Started](learn/getting-started.md) for a line-by-line walkthrough of the first two-step workflow
- [Core Concepts](learn/core-concepts.md) for the Task / Node / Workflow model
- [Recommended Patterns](learn/recommended-patterns.md) for the preferred first-use forms
- [Linear Workflows](guides/linear-workflows.md) and [Data Binding](guides/data-binding.md) for the first practical steps
- [Runtime Behavior](reference/runtime-behavior.md) for exact result, outputs, branching, and join semantics
- [Python Reference](reference/python-api.md) for generated API docs
