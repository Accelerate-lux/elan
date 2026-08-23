# Elan

**Explicit orchestration for AI-written dynamic workflows.**

Elan is a graph-native Python orchestrator for AI and data workflows whose
shape may emerge while they run. Business work stays in typed tasks; routing,
fan-out, joins, context, policy, and runtime graph growth stay visible in the
workflow declaration.

Elan's product direction is orchestration that is **AI-writable,
human-reviewable, and machine-validatable**.

!!! warning "Alpha software"
    APIs may change. Use the [capability status](status.md) as the canonical
    source for what is Available, Experimental, Planned, or Direction.

## The product thesis

AI makes producing plausible orchestration code inexpensive. It does not make
generated control flow easier to review. Elan treats the workflow declaration
as a durable review artifact:

- tasks describe work;
- nodes and joins describe topology;
- typed bindings describe data movement;
- policy describes execution-shape permissions;
- `Expand` marks the one place where runtime values may grow the graph.

## Current surface

| Capability | Model fit | Implementation status |
| --- | --- | --- |
| Workflows, binding, routing, joins, context, and composition | Native | **Available** |
| Yield-driven multiplicity and sibling concurrency | Native | **Available** |
| Runtime graph materialization | Native | **Experimental** |
| Direct registered-task invocation | Native | **Planned** |
| Declaration-only graph inspection | Native | **Planned** |
| Durable and remote execution | Compatible direction | **Direction** |

“Native” describes fit with Elan's model. It does not override implementation
status.

## Start here

- [Getting Started](learn/getting-started.md) for the first workflow
- [Core Concepts](learn/core-concepts.md) for Task / Node / Workflow
- [AI Authoring](learn/ai-authoring.md) for coding-agent instructions,
  canonical patterns, and anti-patterns
- [Dynamic Execution](guides/dynamic-execution.md) for `Expand` and `Fragment`
- [Adaptive Research](guides/adaptive-research.md),
  [Document Decisioning](guides/document-decisioning.md), and
  [ETL Recovery](guides/etl-recovery.md) for complete dynamic scenarios
- [Runtime Behavior](reference/runtime-behavior.md) for exact semantics
- [Comparison Summary](comparison/summary.md) for the adjacent-tool assessment
