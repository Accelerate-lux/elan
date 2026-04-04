# What "Dynamic" Means Across Workflow Tools

The word `dynamic` is overloaded in orchestration tooling. Different tools use it to describe very different capabilities, which makes side-by-side comparison noisy unless the term is broken down more carefully.

For the rest of this comparison set, it helps to distinguish three separate meanings:

1. `Runtime multiplicity`
  The workflow can decide at runtime to run a known step multiple times or to choose among predefined branches.
2. `Runtime control flow`
  The workflow can revisit steps, join dynamic branches, or support some form of loop or recursion.
3. `Runtime graph materialization`
  The workflow can materialize new workflow structure at runtime by inserting new nodes, fragments, or child workflows that were not fully declared up front.

The first two are common. The third is much rarer, and it is the distinction that matters most when comparing Elan to the rest of this set.

## Summary table


| Tool      | What `dynamic` usually means                         | Runtime multiplicity | Runtime control flow | Runtime graph materialization | How it works                                                                         | Main limit                                                                                          |
| --------- | ---------------------------------------------------- | -------------------- | -------------------- | ----------------------------- | ------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------- |
| Airflow   | Dynamic task mapping inside a DAG                    | Strong               | Weak                 | N/A                           | `expand()`, branching, scheduler-created mapped task instances                       | The graph model remains an acyclic DAG                                                              |
| Prefect   | Plain Python control flow inside flows               | Moderate             | Moderate             | Weak                          | Regular Python `if` / loops, tasks, nested flows                                     | The graph is flexible in code, but not graph-materializing as a first-class orchestration primitive |
| Dagster   | Dynamic duplication of known graph regions           | Strong               | Weak                 | N/A                           | `DynamicOut`, `.map(...)`, `.collect()`                                              | Dynamic behavior stays inside a DAG of compute                                                      |
| Metaflow  | Branches, foreach, joins, and special-case recursion | Strong               | Moderate             | N/A                           | `self.next(...)`, `foreach`, joins, conditional transitions, step self-recursion     | Recursion is narrow and the flow remains DAG-shaped overall                                         |
| Temporal  | Durable imperative workflow control flow             | Moderate             | Strong               | Weak                          | workflow code, child workflows, signals, timers, Continue-As-New                     | Strong runtime coordination, but not graph-native workflow growth                                   |
| LangGraph | Dynamic traversal of a compiled state graph          | Strong               | Strong               | Weak                          | conditional edges, `Send`, `Command`, subgraphs                                      | Highly flexible routing, but not arbitrary runtime graph construction                               |
| Elan      | Runtime graph growth as part of the model            | Native               | Native               | Native                        | `Expand(...)`, callable `next`, fragments, child workflows, append-only continuation | Expansion is broad but still bounded by validation and guardrails                                   |


Legend: `Native` means the capability is part of the tool's core model. `N/A` means the tool's graph model does not support that category directly.

## Airflow

In Airflow, `dynamic` mainly means the scheduler can create multiple runtime task instances from a mapped task. That is real dynamism, but it is multiplicity within a DAG, not runtime graph authoring. The structure is still an Airflow DAG, and branching still resolves among predefined downstream tasks.

That makes Airflow dynamic in the sense of "how many instances of this known task should run?" but not in the sense of "what new workflow structure should be materialized now?"

## Prefect

Prefect is different because its main dynamic feature is not a graph primitive at all. It is ordinary Python control flow in a flow function. If a workflow needs an `if`, a loop, or a nested call to another flow, Prefect can often express that naturally because the flow is just Python.

That makes Prefect more flexible than DAG tools at the control-flow level, but it still does not center runtime graph materialization as an explicit orchestration concept. The flexibility is mostly imperative-programming flexibility rather than graph-expansion flexibility.

## Dagster

Dagster's dynamic model is strongest around dynamic mapping and collection. It can duplicate a known portion of the graph based on runtime values and then collect results downstream. That is broader than static scheduling, but it is still a DAG-oriented form of dynamism.

In other words, Dagster supports runtime duplication of known compute structure, not open-ended runtime graph growth.

## Metaflow

Metaflow supports branching, `foreach`, joins, and now conditional and recursive steps. This gives it a richer interpretation of `dynamic` than Airflow or Dagster if the comparison includes joins and limited recursion.

The important limit is that Metaflow's recursion is a special case: a step may recurse to itself, but the system is still documented as a DAG model rather than a general cyclic graph runtime. So Metaflow's dynamic story is meaningful, but still narrower than graph-native expansion.

## Temporal

Temporal is dynamic mainly through durable workflow code. A Temporal workflow can branch, loop, wait on timers, react to signals, start child workflows, and Continue-As-New into a fresh execution chain. That gives it strong runtime control-flow power and strong compositional durability, but it is not the same thing as runtime graph materialization.

The workflow remains code that drives durable execution and replay, not a graph that grows by materializing new nodes or fragments into the active topology. So Temporal is broader than DAG tools on long-running control flow, but it is still solving a different problem than Elan's graph-native expansion model.

## LangGraph

LangGraph is the strongest non-Elan example in this doc if the question is "how far beyond mapping and branching does the tool go?" It supports conditional edges, loops, `Send` for map-reduce fan-out, `Command` for routing plus state updates, and subgraphs. That gives it strong runtime control-flow expressiveness.

Still, LangGraph's flexibility is best understood as dynamic traversal and coordination within a compiled graph runtime. If a node routes to a subgraph or agent-like component, it is still invoking predeclared graph structure rather than materializing new workflow structure into the active graph. Its model is stateful graph execution, not workflow growth as a first-class primitive.

## Elan

Elan uses the widest definition of `dynamic` in this comparison set. In Elan's model, runtime logic may expand the active workflow by returning:

- `None`
- a `Node`
- a workflow-shaped fragment
- a `Workflow`

This happens through callable `next` or explicit `Expand(...)`, optionally with a static `then` continuation anchor. That means Elan is not limited to "run this existing task many times" or "choose among these predefined routes." It can materialize new workflow structure at runtime and continue from it.

That said, Elan is not an unrestricted graph mutation model. The internal design notes are explicit about the boundaries:

- expansion is append-only
- already materialized nodes and routes are not rewritten
- each materialized graph segment must validate in its current form
- nested and recursive expansion are controlled by guardrails

So the right claim is not "Elan can do anything." The right claim is that Elan treats runtime graph growth as part of the orchestration model itself, which is substantially broader than the other interpretations of `dynamic` in this comparison set.

## Why this matters for the comparison

If all of these tools are evaluated under one generic `Dynamic Graphs` label, they look more similar than they really are. A more accurate reading is:

- Airflow and Dagster are dynamic mainly in multiplicity
- Prefect is dynamic mainly in imperative control flow
- Temporal is dynamic mainly in durable imperative control flow
- Metaflow is dynamic in structured branching, joins, and narrow recursion
- LangGraph is dynamic in graph traversal and stateful coordination
- Elan is dynamic in runtime graph materialization itself

That distinction is the clearest explanation for why Elan sits between scheduler-oriented orchestrators and agent runtimes while still differing from both.

## References

- Airflow DAGs: [https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dags.html](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dags.html)
- Airflow dynamic task mapping: [https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/dynamic-task-mapping.html](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/dynamic-task-mapping.html)
- Prefect flows: [https://docs.prefect.io/v3/concepts/flows](https://docs.prefect.io/v3/concepts/flows)
- Prefect tasks: [https://docs.prefect.io/v3/concepts/tasks](https://docs.prefect.io/v3/concepts/tasks)
- Dagster overview: [https://docs.dagster.io/](https://docs.dagster.io/)
- Dagster dynamic graphs: [https://docs.dagster.io/guides/build/ops/dynamic-graphs](https://docs.dagster.io/guides/build/ops/dynamic-graphs)
- Metaflow basics: [https://docs.metaflow.org/metaflow/basics](https://docs.metaflow.org/metaflow/basics)
- Temporal docs home: [https://docs.temporal.io/](https://docs.temporal.io/)
- Temporal developer guide: [https://docs.temporal.io/develop](https://docs.temporal.io/develop)
- Temporal Python SDK guide: [https://docs.temporal.io/develop/python](https://docs.temporal.io/develop/python)
- Temporal child workflows: [https://docs.temporal.io/develop/python/child-workflows](https://docs.temporal.io/develop/python/child-workflows)
- Temporal Continue-As-New: [https://docs.temporal.io/develop/python/continue-as-new](https://docs.temporal.io/develop/python/continue-as-new)
- LangGraph overview: [https://docs.langchain.com/oss/python/langgraph/overview](https://docs.langchain.com/oss/python/langgraph/overview)
- LangGraph graph API: [https://docs.langchain.com/oss/python/langgraph/graph-api](https://docs.langchain.com/oss/python/langgraph/graph-api)
- Elan public API and behavior overview: [../reference/api.md](../reference/api.md)
- Elan execution model and branching overview: [../reference/runtime-behavior.md](../reference/runtime-behavior.md)
