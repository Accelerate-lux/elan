# Dynamic Model

This page explains what Elan means by `dynamic` and why that matters for its design.

Elan treats dynamic workflow behavior more broadly than tools that only support:

- runtime multiplicity
- imperative runtime control flow
- traversal of a precompiled graph

The intended direction is runtime graph materialization as part of the orchestration model itself.

## Current state

Today, the runtime already supports:

- explicit branching
- fan-out
- conditional multi-routing
- terminal join on `result`
- concurrent execution of sibling runnable branches

## Planned direction

The broader dynamic model still points toward:

- runtime graph expansion
- callable continuations
- composition
- cycles with guardrails

## Related reading

- [Design Philosophy](../design_philosophy.md)
- [Comparisons / Dynamic Models](../comparison/dynamic_models.md)
- [Status](status.md)
