# Design Philosophy

## Goal

Elan is meant to be a simple, flexible, and coherent orchestrator for
workload-agnostic workflows.

The goal is not to specialize in one kind of workload, but to provide a
consistent model for workflows that may combine data processing, service calls,
agent execution, branching, fan-out, synchronization, and long-running control
flow.

## Core Idea

Elan is built around the idea that workflows are often only partially known
upfront. Some workflows stay simple and linear. Others branch, expand, recurse,
or synchronize dynamically as they run.

Instead of treating that as an edge case, Elan treats dynamic graph execution as
part of the core model.

## Principles

- Workflows are first-class
- Graph structure stays explicit
- Dynamic branching, fan-out, and synchronization stay natural
- Execution units compose cleanly across different kinds of workloads
- Code, config, and API submission share the same model
- The local development experience stays straightforward
- The interface stays small, stable, and easy to reason about

## What Elan Is Trying To Be

- A general-purpose orchestrator, not just a DAG scheduler
- A mixed-workload engine, not just an agent runtime
- A graph-native system that handles dynamic execution naturally
- A tool that stays usable for small workflows without collapsing under more
  complex ones

## What Elan Is Not Trying To Be

- A Kubernetes-first platform
- A framework tied to a single execution backend
- An LLM-only orchestration layer
- A large platform whose complexity shows up in every basic workflow

## Design Direction

Elan favors a small core interface and clear semantics over feature sprawl.

The intent is to make simple workflows feel simple, while keeping the model
strong enough to support branching, fan-out, recursive barriers, sub-workflows,
and dynamic graph expansion without introducing a different programming model.

Developer experience is a core concern. Elan is easy to learn, predictable
to operate, and practical to move from local development to production.
