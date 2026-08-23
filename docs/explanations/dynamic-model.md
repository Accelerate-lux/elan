# Dynamic Model

This page explains what Elan means by `dynamic` and why that matters for its design.

Elan treats dynamic workflow behavior more broadly than tools that only support:

- runtime multiplicity
- imperative runtime control flow
- traversal of a precompiled graph

Runtime graph materialization is now part of the orchestration model itself.

## Current state

Today, the runtime already supports:

- explicit branching
- fan-out
- conditional multi-routing
- workflow-wide terminal joins
- activation-scoped mid-graph joins
- concurrent execution of sibling runnable branches
- append-only `Expand(...)` materialization of self-routed `Fragment` graphs
- nested and recursive expansion with lexical target resolution

## Remaining direction

The broader dynamic model still points toward safe executable cycles, expansion
budgets, richer observability, and config/API parity.

Callable continuation shorthand and expansion lifecycle continuations are
deferred beyond the initial expansion contract.

## Related reading

- [Comparisons / Dynamic Models](../comparison/dynamic_models.md)
- [Status](../status.md)
