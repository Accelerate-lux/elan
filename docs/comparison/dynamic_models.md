# What “Dynamic” Means Across Workflow Tools

_Reviewed against primary documentation in August 2026._

The word `dynamic` describes several different orchestration capabilities. This
comparison separates three meanings:

1. **Runtime multiplicity:** a runtime value creates multiple instances of a
   known step or selects among predefined routes.
2. **Runtime control flow:** execution may loop, recurse, wait, resume, or
   coordinate dynamic branches.
3. **Runtime graph materialization:** execution appends new named workflow
   structure that was not fully declared in the original graph.

## Summary

| Tool | Primary dynamic model | Multiplicity | Control flow | Graph materialization | Mechanism | Main boundary |
| --- | --- | --- | --- | --- | --- | --- |
| Airflow | Mapped tasks inside a DAG | Strong | Weak | N/A | `expand()`, branching | Topology is intended to remain a DAG |
| Prefect | Imperative Python flow execution | Moderate | Moderate | Weak | Python control flow, tasks, subflows | Dynamism is primarily code execution |
| Dagster | Runtime duplication of graph regions | Strong | Weak | N/A | `DynamicOut`, `map`, `collect` | Known downstream regions are cloned |
| Metaflow | Branches, foreach, joins, step recursion | Strong | Moderate | N/A | `self.next`, `foreach`, conditionals | Recursion is a single-step special case |
| Temporal | Durable imperative execution | Moderate | Strong | Weak | workflow code, messages, timers, child workflows | Event history and replay are central |
| LangGraph | Dynamic traversal of a compiled state graph | Strong | Strong | Weak | conditional edges, `Send`, `Command`, subgraphs | Nodes and state graph are compiled ahead |
| Elan | Append-only runtime fragments | Native | Native | Native (**Experimental**) | `Expand`, `Fragment`, atomic candidate validation | No budgets or serialized final graph |

`Native` is architectural fit. Elan maturity appears separately in parentheses
and resolves to [Capability status](../status.md).

## Reading the distinctions

Airflow's dynamic task mapping creates a variable number of task instances from
runtime data, while its documentation recommends keeping DAG topology stable.
Dagster similarly duplicates declared downstream op regions through dynamic
outputs, mapping, and collection.

Prefect gets much of its flexibility from executing ordinary Python inside a
flow. This is concise and expressive, but the dynamic decision is imperative
control flow rather than a separately materialized graph declaration.

Metaflow combines explicit branching, foreach, joins, conditionals, and, since
Metaflow 2.18, recursion of one step. Its documentation still describes flows
as DAGs and recursion as a special case rather than arbitrary graph mutation.

Temporal provides the strongest durability model in this set. Workflows can
branch, loop, wait on messages and timers, spawn child workflows, and
Continue-As-New with a fresh history. Those are durable execution semantics,
not runtime growth of an inspectable graph.

LangGraph supports loops, subgraphs, map-reduce fan-out through `Send`, and
routing plus state updates through `Command`. The exact dynamic edges may be
chosen at runtime, but execution traverses nodes in a compiled shared-state
graph.

Elan's Experimental `Expand` contract receives a typed value and appends one
namespaced, self-routed `Fragment` after validating the combined candidate
graph. Expansion is append-only: it does not rewrite previously materialized
nodes or routes. Nested and recursive expansion exist, but builders must
terminate themselves because depth and total-materialization budgets are
**Planned**.

## References

- [Airflow DAGs](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dags.html)
- [Airflow dynamic task mapping](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/dynamic-task-mapping.html)
- [Prefect flows](https://docs.prefect.io/v3/concepts/flows)
- [Prefect tasks](https://docs.prefect.io/v3/concepts/tasks)
- [Dagster dynamic graphs](https://docs.dagster.io/guides/build/ops/dynamic-graphs)
- [Metaflow basics](https://docs.metaflow.org/metaflow/basics)
- [Temporal child workflows](https://docs.temporal.io/develop/python/workflows/child-workflows)
- [Temporal Continue-As-New](https://docs.temporal.io/develop/python/workflows/continue-as-new)
- [LangGraph graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [Elan API overview](../reference/api.md)
- [Elan runtime behavior](../reference/runtime-behavior.md)
