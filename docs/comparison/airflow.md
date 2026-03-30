# Airflow

Airflow is the scheduler-oriented baseline in this comparison set. For the shared scenario, see [baseline_workflow.md](./baseline_workflow.md). For the dynamic taxonomy used across these docs, see [dynamic_models.md](./dynamic_models.md).

## What this tool is best at

Airflow is strongest when the workflow is fundamentally a scheduled DAG with explicit task dependencies, operational controls, and a mature scheduler model. It is a natural reference point for teams coming from batch and data platform orchestration.

## Capabilities assessment

Airflow is dynamic mainly in the sense of runtime multiplicity. On the shared baseline, it can fan out with dynamic task mapping and can choose among predefined downstream tasks with branching, but both behaviors still live inside a scheduler-managed DAG.

That means Airflow is not dynamic in the stronger Elan sense of runtime graph materialization. The scheduler can create runtime task instances from known task definitions, but the workflow is still an acyclic DAG rather than an append-only graph that can materialize new nodes or fragments as execution proceeds.

Routing is explicit at the dependency level, but conditional behavior is task-id and skip based. Cycles are not supported at all, so runtime control flow stays limited compared with graph-native orchestration models. Composition exists through DAG-level structuring and grouping, but it is not the center of the model in the way reusable sub-workflows are in Elan.

Airflow's workload scope is broader than data transformation alone, but the overall model still reads most naturally for scheduler-led orchestration rather than mixed dynamic graph workflows.

## Usage assessment

Airflow is readable for straightforward dependency chains, especially for teams already familiar with DAG authoring. The friction shows up when the graph becomes more dynamic. Mapped tasks, branching, task IDs, and trigger rules can make a small workflow feel more operationally shaped than conceptually shaped.

Business logic can still live in Python callables, but orchestration concerns leak into the flow earlier than in Elan. Testing is reasonable at the task level, yet the branch and downstream behavior are easier to understand once you are thinking in Airflow terms, not just Python terms.

Predictability is high once you understand Airflow's scheduler rules. The tradeoff is that the mental model is the scheduler.

## Where it fits well

Airflow fits well when the primary need is reliable scheduled DAG execution with explicit dependencies and familiar operational patterns. It is a strong baseline when the workflow is mostly static and the team already thinks in terms of tasks, runs, and scheduler behavior.

## Where it becomes awkward for Elan-style workflows

Airflow becomes less natural when the workflow shape is part of the problem itself. Dynamic fan-out is supported, but graph growth, conditional routing, and downstream joins are still interpreted through DAG execution and skip semantics. That makes partially known workflows feel more indirect than they do in a graph-native model.

## Elan takeaway

Compared with Airflow, Elan is easier to position as a workflow-first rather than scheduler-first system. The added value is not that Elan can "also branch" or "also fan out," but that routing, dynamic execution, and result boundaries stay closer to the workflow definition instead of being mediated by scheduler conventions such as task IDs, skipped paths, and trigger rules.

## References

- Airflow dynamic task mapping: https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/dynamic-task-mapping.html
- Airflow DAG concepts and branching: https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dags.html
