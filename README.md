# Elan

**Explicit orchestration for AI-written dynamic workflows.**

Elan is a graph-native Python orchestrator for AI and data workflows whose
shape may emerge while they run. It keeps business work in typed tasks and puts
routing, fan-out, joins, context, policy, and runtime graph growth in explicit
workflow declarations.

The goal is orchestration that is **AI-writable, human-reviewable, and
machine-validatable**. Code generation makes syntax cheaper; Elan focuses on
leaving behind control flow that people and tools can inspect and reason about.

> Elan is alpha software. APIs may change. Check the
> [capability status](https://accelerate-lux.github.io/elan/status/) before
> relying on a feature.

## Why Elan

- **Explicit topology:** Routing decisions live in `Node`, `When`, `Join`, and
  `Workflow` declarations instead of disappearing inside task bodies.
- **Typed boundaries:** Pydantic payloads and `Binder[...]` make important data
  movement visible and validate it early.
- **One dynamic boundary:** A typed `Expand` builder can materialize a validated,
  namespaced `Fragment` when a runtime plan determines graph structure.
- **Mixed workloads:** The same model covers deterministic data processing,
  agent planning, service coordination, and human-review boundaries.
- **Composition:** Child workflows remain ordinary graph nodes with explicit
  result boundaries.

## Maturity at a glance

| Capability | Model fit | Implementation status |
| --- | --- | --- |
| Workflows, binding, routing, joins, context, and composition | Native | **Available** |
| Yield-driven multiplicity and sibling concurrency | Native | **Available** |
| Runtime `Expand` / `Fragment` materialization | Native | **Experimental** |
| Direct invocation of registered tasks | Native | **Planned** |
| Declaration-only graph inspection | Native | **Planned** |
| Persistence, retries/resume, and remote workers | Compatible direction | **Direction** |

“Native” describes architectural fit; it never means a capability is
implemented. The canonical definitions of **Available**, **Experimental**,
**Planned**, and **Direction** are on the
[status page](https://accelerate-lux.github.io/elan/status/).

## Installation

The `elan-workflow` package is not published on PyPI yet. Install the current
source explicitly:

```bash
pip install "elan-workflow @ git+https://github.com/Accelerate-lux/elan.git"
```

Elan requires Python 3.11 or newer.

## Quickstart

```python
import asyncio

from elan import Node, Workflow, task


@task
def prepare(name: str) -> str:
    return name.strip().title()


@task
async def greet(name: str) -> str:
    return f"Hello, {name}!"


workflow = Workflow(
    "greeting",
    start=Node(run=prepare, next="greet"),
    greet=greet,
)

run = asyncio.run(workflow.run(name="world"))
assert run.result == "Hello, World!"
```

The constructor form is compact for examples and generated declarations. For
application workflows, prefer a dedicated `Workflow` subclass.

## Dynamic examples

Three credential-free guides use the same Experimental primitive in different
domains:

- [Adaptive research](https://accelerate-lux.github.io/elan/guides/adaptive-research/)
- [Document decisioning](https://accelerate-lux.github.io/elan/guides/document-decisioning/)
- [AI-assisted ETL recovery](https://accelerate-lux.github.io/elan/guides/etl-recovery/)

## Documentation

- [Hosted documentation](https://accelerate-lux.github.io/elan/)
- [AI authoring guide](https://accelerate-lux.github.io/elan/learn/ai-authoring/)
- [Runtime behavior](https://accelerate-lux.github.io/elan/reference/runtime-behavior/)
- [Python API](https://accelerate-lux.github.io/elan/reference/python-api/)
- [Tool comparisons](https://accelerate-lux.github.io/elan/comparison/summary/)

The name, pronounced “ay-lan,” comes from the French *élan*: both momentum and
moose.

![Elan](elan-pic.webp)
