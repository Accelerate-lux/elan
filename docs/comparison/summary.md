# Tool Comparison Summary

_Reviewed against primary documentation in August 2026._

Elan sits between scheduler-oriented orchestrators and agent graph runtimes. The
tools in this set can all express meaningful dynamic behavior, but they differ
in what “dynamic” means, where routing lives, and which operational guarantees
are central to the product.

This is a programming-model assessment, not a benchmark. See the
[shared baseline](baseline_workflow.md) and
[dynamic taxonomy](dynamic_models.md).

## Capabilities

| Tool | Runtime multiplicity | Runtime control flow | Runtime graph materialization | Explicit routing | Composition | Workload breadth |
| --- | --- | --- | --- | --- | --- | --- |
| Airflow | Strong | Weak | N/A | Moderate | Moderate | Moderate |
| Prefect | Moderate | Moderate | Weak | Weak | Strong | Strong |
| Dagster | Strong | Weak | N/A | Moderate | Strong | Moderate |
| Metaflow | Strong | Moderate | N/A | Strong | Moderate | Moderate |
| Temporal | Moderate | Strong | Weak | Weak | Strong | Strong |
| LangGraph | Strong | Strong | Weak | Strong | Strong | Moderate |
| Elan | Native | Native | Native (**Experimental**) | Native | Native | Strong |

`Native` describes fit with a tool's model. For Elan, the parenthesized label is
the separate implementation maturity from the
[canonical status ledger](../status.md). `N/A` means the category falls outside
the tool's graph model rather than being a weaker implementation of it.

## Usage

| Tool | Mental model | Low boilerplate | Task/orchestration separation | Testability | Operational maturity |
| --- | --- | --- | --- | --- | --- |
| Airflow | Moderate | Weak | Moderate | Moderate | Strong |
| Prefect | Strong | Strong | Moderate | Strong | Strong |
| Dagster | Moderate | Moderate | Moderate | Strong | Strong |
| Metaflow | Strong | Moderate | Moderate | Moderate | Strong |
| Temporal | Moderate | Moderate | Moderate | Strong | Strong |
| LangGraph | Moderate | Weak | Weak | Moderate | Strong |
| Elan | Strong | Strong | Native | Moderate | Weak |

These qualitative ratings describe relative fit within this comparison set.
Elan does not currently provide persistence, retries/resume, remote workers, or
an operational control plane. Those capabilities are separately classified as
**Direction**, not as implemented features.

## AI-era interpretation

AI reduces the importance of saving a few lines of authoring syntax. It raises
the importance of stable concepts, explicit review artifacts, precise
validation, and documentation that an authoring agent can retrieve.

That shift helps Elan's declaration-oriented model, but it also strengthens
mature tools: agents have more Prefect, Airflow, Dagster, Temporal, and
LangGraph examples to learn from, while those products already provide broader
operational surfaces. Elan's current claim is therefore narrow:

> Elan uses declared routing and has Experimental support for adding graph
> fragments at runtime.

Direct registered-task invocation and declaration-only graph inspection would
strengthen that review loop, but both are **Planned** rather than current.

## Per-tool takeaway

- [Airflow](airflow.md) is the scheduler baseline: mature scheduled DAGs and
  runtime task mapping, with topology intended to remain relatively stable.
- [Prefect](prefect.md) is the Python-first baseline: compact imperative flows,
  directly invoked instrumented tasks, deployments, retries, and broad
  operations. Elan trades compactness for declared routing.
- [Dagster](dagster.md) is the data-platform baseline: strong dynamic mapping,
  collection, lineage, and structured data orchestration.
- [Metaflow](metaflow.md) is an explicit step/branch/join baseline with foreach
  and special-case recursive steps.
- [Temporal](temporal.md) is the durable-execution baseline: replay, timers,
  messages, child workflows, and Continue-As-New solve a different primary
  problem from graph materialization.
- [LangGraph](langgraph.md) is the closest agent-runtime comparator: strong
  loops, subgraphs, `Send`, and `Command` over a compiled state graph.

## Overall takeaway

Elan should not be selected today for operational breadth. It is most relevant
when a team values explicit task/orchestration separation and needs a runtime
plan to materialize validated workflow structure. The Experimental label is
important: the primitive exists, but budgets, final graph serialization,
durability, and remote execution do not.
