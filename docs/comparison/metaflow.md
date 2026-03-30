# Metaflow

Metaflow is the explicit step-and-join baseline in this comparison set. For the shared scenario, see [baseline_workflow.md](./baseline_workflow.md). For the dynamic taxonomy used across these docs, see [dynamic_models.md](./dynamic_models.md).

## What this tool is best at

Metaflow is strongest when a workflow should read as an explicit sequence of steps, branches, joins, and foreach loops. It is approachable for developers who want orchestration that is visible in code without moving all the way to a lower-level graph API.

## Capabilities assessment

Metaflow is broader than Airflow or Dagster on dynamic control flow because it combines branching, `foreach`, explicit joins, conditional transitions, and a narrow recursion pattern. On the shared baseline, that makes it one of the clearest comparators for structured dataflow with explicit join behavior.

The important limit is where that dynamism stops. Metaflow's recursion support is still documented as a special case inside a DAG model, not as arbitrary graph cycles, and runtime graph materialization is outside the model. In practice, that makes Metaflow stronger on structured control flow than on open-ended graph evolution.

Composition is possible through the way flows are structured, but reusable sub-workflows are not the center of the programming model in the same way they are in Elan. Metaflow's workload scope is broader than a narrow pipeline tool, but the model still reads most naturally as step-based dataflow orchestration.

## Usage assessment

Metaflow is one of the more readable tools in this comparison set for explicit branching and joins. The `@step` plus `self.next(...)` style makes control flow visible, and the foreach and join patterns are easy to follow.

The tradeoff is that business logic and orchestration are closer together than in Elan. State lives on `self`, transitions are declared imperatively, and the workflow remains bound to the step class structure. Boilerplate is moderate. Predictability is strong once the flow is laid out, but the model is less cleanly separated than Elan's task-plus-node split.

## Where it fits well

Metaflow fits well when the team wants explicit code-level orchestration with clear branching, joins, and foreach behavior, especially in data and experimentation workflows where step structure is a good match.

## Where it becomes awkward for Elan-style workflows

Metaflow becomes less natural when the comparison turns toward graph-native composition and routing as first-class concepts. It can represent substantial control flow, but it does so through a step class with imperative transitions and persisted state, rather than through a small declarative workflow surface with reusable sub-workflows as standard nodes.

## Elan takeaway

Compared with Metaflow, Elan's added value is cleaner separation of concerns. Metaflow is explicit, which is a real strength. Elan pushes that explicitness further by separating pure task code from routing code, making composition more uniform and keeping dynamic graph behavior closer to the workflow definition instead of the step object's state and transition methods.

## References

- Metaflow basics: https://docs.metaflow.org/metaflow/basics
