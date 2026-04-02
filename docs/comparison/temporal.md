# Temporal

Temporal is the durable-execution baseline in this comparison set. For the shared scenario, see [baseline_workflow.md](./baseline_workflow.md). For the dynamic taxonomy used across these docs, see [dynamic_models.md](./dynamic_models.md).

## What this tool is best at

Temporal is strongest when the workflow is long-running, failure-sensitive, and operationally important enough that durable execution is the primary concern. It is built around the idea that workflows should survive crashes, retries, outages, and restarts without losing progress.

## Capabilities assessment

Temporal is dynamic mainly through durable imperative control flow. A workflow can branch, loop, wait on timers, react to signals, spawn child workflows, and use Continue-As-New to roll execution forward with a fresh event history. That gives it strong runtime control-flow power, but the flexibility lives inside workflow code rather than inside a graph-materializing workflow DSL.

That distinction matters for this comparison set. Temporal can decide at runtime which activities or child workflows to execute and when to execute them, but it is not a graph-native system that materializes new nodes, fragments, or workflow topologies into an active graph in the Elan sense.

Composition is strong through child workflows. Workload breadth is strong as well because Temporal is not tied to data pipelines or agent-only workloads. The main limit is that the model is centered on durable workflow replay, determinism, and event history rather than explicit graph structure.

## Usage assessment

Temporal gives developers a powerful reliability model, but it also imposes a stricter mental model than most of the other tools in this set. Workflow code has determinism constraints, replay matters, and the user has to think in terms of workflow history, activities, workers, and durable execution boundaries.

That makes the system predictable once understood, but less lightweight than Elan for ordinary workflow authoring. Separation between business logic and orchestration is reasonable through the workflow and activity split, yet orchestration concerns remain highly visible because durability is the center of the abstraction. Boilerplate is moderate, testability is decent, and predictability is strong once the Temporal model is internalized.

## Where it fits well

Temporal fits well when reliability, resumability, retries, timers, and long-running execution semantics are the main problem. It is a strong comparator for workflows that need to survive infrastructure failure or coordinate complex, durable business processes over time.

## Where it becomes awkward for Elan-style workflows

Temporal becomes less natural when the comparison turns toward graph shape, explicit routing vocabulary, and runtime graph growth as the primary abstraction. It can absolutely express substantial control flow, but it does so as durable workflow code, not as a graph-native orchestration surface where routing and graph materialization are explicit first-class concepts.

## Elan takeaway

Compared with Temporal, Elan's added value is not stronger durability semantics. The value is a clearer orchestration model for graph-shaped dynamic workflows. Temporal is the right comparator when the buyer asks about durable execution and reliability guarantees. Elan is the stronger fit when the buyer asks for explicit routing, composable graph growth, and a workflow model that stays close to the graph itself instead of centering replay and workflow history.

## References

- Temporal docs home: https://docs.temporal.io/
- Temporal developer guide: https://docs.temporal.io/develop
- Temporal Python SDK guide: https://docs.temporal.io/develop/python
- Temporal child workflows: https://docs.temporal.io/develop/python/child-workflows
- Temporal Continue-As-New: https://docs.temporal.io/develop/python/continue-as-new
