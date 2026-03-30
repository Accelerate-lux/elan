# LangGraph

LangGraph is the graph-native agent-runtime baseline in this comparison set. For the shared scenario, see [baseline_workflow.md](./baseline_workflow.md). For the dynamic taxonomy used across these docs, see [dynamic_models.md](./dynamic_models.md).

## What this tool is best at

LangGraph is strongest when the workflow is genuinely agentic: stateful, branching, iterative, and often built around tool use, interrupts, and multi-step reasoning. It is one of the closest comparators to Elan on graph shape, but it approaches the problem through shared state and graph runtime primitives.

## Capabilities assessment

LangGraph is the strongest tool in this set other than Elan on runtime control flow. On the shared baseline, it can express conditional edges, dynamic fan-out with `Send`, subgraphs, and loops directly in the graph API. That gives it strong support for the kinds of branching and iterative execution patterns that matter in Elan's positioning.

The key difference is where the flexibility lives. LangGraph is state-centric. Nodes operate on shared state, routing happens through edge functions or `Command`, and the user thinks in terms of graph execution primitives. That is powerful, but it is dynamic traversal and coordination within a compiled state graph, not runtime graph materialization in the Elan sense.

Cycles and recursive behavior are first-class enough to be operationally acknowledged in the runtime through recursion limits. Composition is strong through subgraphs. Workload breadth is meaningful, but the system is still most naturally framed around agent workflows and stateful graph execution rather than append-only workflow growth.

## Usage assessment

LangGraph is expressive, but it is mechanically heavier than Elan for ordinary workflow authoring. The user needs to define state schemas, state reducers, nodes, and edge behavior explicitly. That makes the workflow precise, but it also means more framework surface area shows up in even small examples.

Testability is reasonable because nodes are still functions, but the surrounding behavior is tightly coupled to shared state conventions. Predictability is moderate: the graph is explicit, yet understanding it often requires tracking how state is accumulated, merged, and routed, not just how tasks connect.

## Where it fits well

LangGraph fits well when the workflow is truly agent-oriented and benefits from explicit state machines, interrupts, subgraphs, and rich control over graph execution. It is especially well matched to complex reasoning loops and tool-driven agent patterns.

## Where it becomes awkward for Elan-style workflows

LangGraph becomes less attractive when the workflow does not need a state-machine-centric model. For general orchestration, especially mixed data and service workflows, the state schema and graph API can feel lower level than necessary. The workflow is explicit, but not especially lightweight.

## Elan takeaway

Compared with LangGraph, Elan's added value is a higher-level orchestration surface for the same general class of dynamic graph problems. It keeps routing explicit without forcing the workflow to be expressed as a shared-state machine, which makes many mixed and non-agent workflows read more like task orchestration and less like graph runtime programming.

## References

- LangGraph overview: https://docs.langchain.com/oss/python/langgraph/overview
- LangGraph graph API: https://docs.langchain.com/oss/python/langgraph/graph-api
