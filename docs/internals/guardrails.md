# Guardrails

This document captures the guardrails that constrain workflow execution in Elan.

**Status: design-only for runtime graph expansion and recurrence.** The current
runtime implements static-cycle detection plus the
`WorkflowPolicy.allow_cycles` and `allow_runtime_expansion` declaration flags,
but it does not execute graph expansion or provide recurrence budgets. Current
join behavior is documented separately because activation-scoped joins were
implemented after the original guardrails proposal.

It separates:

- structural guardrails, which are part of the graph model itself
- runtime guardrails, which are execution policies and budgets

The structural guardrails are part of the design now.

The runtime guardrails are outlined here as the next design surface.

## Structural Guardrails

Structural guardrails are hard validity rules.

They define which kinds of graph evolution are allowed at all.

### 1. Append-Only Materialization

Dynamic execution may append graph structure at runtime.

It may not:

- rewrite already materialized nodes
- delete already materialized nodes
- retarget already materialized routes

This keeps runtime graph evolution monotonic and inspectable.

### 2. Valid Current Graph After Each Expansion

Every expansion must leave the graph valid in its current materialized form.

Elan does not allow an expansion to create a temporarily broken graph and rely on a later expansion to fix it.

If a returned structure is invalid now, it is invalid.

### 3. A Fragment Owns Its Entry And Routes

An expansion builder returns one `Fragment` with a declared entry node.

Fragment nodes declare their own internal routes and any routes into existing
static nodes. The runtime does not infer continuation edges or attach an
implicit barrier.

Callable `next` and `then`/`finally`-style expansion continuations are deferred
beyond the initial contract.

### 4. Candidate Graph Validation Is Atomic

The builder return is not appended incrementally. Elan first assigns run-local
identity and constructs a candidate graph containing the existing graph plus the
complete fragment.

Elan validates the candidate as one graph. If validation fails, none of the
fragment is appended or scheduled. Returning `Node`, `Workflow`, or a union of
structural forms is outside the initial contract.

### 5. Expanded Work Inherits Active Join Scopes

`Join` is not restricted to `result`. The current graph language supports
workflow-wide result joins and activation-scoped mid-graph joins.

If runtime expansion is implemented, dynamically added descendants must inherit
active scope membership just like statically routed and yielded descendants.

Whether dynamically returned fragments may declare new joins is still an open
design question and must be resolved before expansion is implemented.

### 6. Dynamic Fragments May Reference Existing Static Nodes, But May Not Mutate Them

A returned fragment may route into already existing static nodes.

That is valid.

What is not valid is mutating those existing static nodes in place.

Dynamic execution may connect to the known graph. It may not rewrite it.

## Runtime Guardrails

Runtime guardrails are not graph-validity rules.

They are execution policies that control graph evolution over time and prevent runaway execution.

The runtime guardrail categories are:

- point-in-time graph budgets
- cumulative graph budgets
- time budgets
- expansion policy toggles

These categories define the runtime policy surface.

### Policy Object

Runtime guardrails live in a workflow-level `Policy` object.

The policy object groups:

- budgets
- validation
- boundaries

Toggle naming follows one rule:

- `allow_...` for capabilities and boundary permissions
- `enable_...` for validation, tracing, and runtime checks

### Point-In-Time Graph Budgets

These budgets limit how large and complex the graph may be at one moment.

Core examples:

- maximum active branches
- maximum materialized nodes live
- maximum expansion depth
- maximum cycle iterations or node visits when cycles are allowed

These are directly correlated to current graph shape, which makes them easier to reason about than more speculative engine-level counters.

### Cumulative Graph Budgets

These budgets limit total graph evolution over the lifetime of a run.

Core examples:

- maximum materialized nodes total
- maximum task executions total

These budgets answer a different question from the point-in-time limits:

- how much graph may exist right now
- how much total work may happen before the run must stop

### Time Budgets

Dynamic execution also needs time-based limits at several scopes.

Core examples:

- task timeout
- workflow timeout
- sub-workflow timeout
- run TTL

These are important because dynamic execution is not only about graph size. It is also about how long one scope is allowed to keep evolving.

### Expansion Policy Toggles

Elan also needs explicit controls for what kinds of dynamic execution are allowed at all.

Core toggles:

- whether a given workflow scope allows `Expand(...)`
- whether a given workflow scope allows static cycles
- whether nested `Expand(...)` is allowed
- whether recursive dynamic expansion is allowed

The workflow-level expansion toggle is especially important because it enables static validation:

- workflows that set `allow_runtime_expansion=False` can be checked statically for forbidden expansion sites
- parent workflows can disable expansion in child scopes without removing dynamic execution globally

This controls graph evolution in sub-workflows without disabling dynamic execution everywhere.

The cycle toggle controls whether a workflow may contain declared recurrence in its static graph.

If cycles are disabled, any static cycle is invalid.

If cycles are enabled, recurrence is controlled by the same budget system that constrains dynamic execution.

These are not structural rules.

They are policy controls that let users choose how much dynamic power is allowed in a given workflow or runtime environment.

### Validation Guardrails

Validation guardrails control how strictly Elan validates a workflow or dynamic expansion before it is allowed to run.

The validation policy surface is:

- validation mode
- static graph validation
- static type validation
- dynamic graph validation
- dynamic type validation
- untyped dynamic expansion policy
- join validation strictness

Validation mode defines the overall strictness profile.

Core profiles:

- `strict`
- `permissive`

Static graph validation and static type validation apply to the known workflow definition.

Dynamic graph validation and dynamic type validation apply when an expansion materializes at runtime.

Untyped dynamic expansion is a separate policy concern.

Dynamic expansion is a more sensitive boundary than ordinary static wiring, so a workflow may allow partially typed static nodes while still forbidding untyped dynamic fragments.

Join validation strictness is also part of this surface.

Core cases:

- whether join contributions must be homogeneous
- whether a join reducer must be typed

### Boundary Guardrails

Boundary guardrails control what a dynamic expansion is allowed to return and how it is allowed to connect to the surrounding graph.

The boundary policy surface is:

- whether expansion is allowed at all
- whether expansions may reference existing static nodes directly
- whether nested `Expand(...)` is allowed
- whether recursive dynamic expansion is allowed

The initial structural return contract is not a policy choice: an expansion
returns exactly one `Fragment`. Bare nodes, workflows, callable `next`, and
`then` continuations are deferred rather than alternate modes.

These rules constrain dynamic graph evolution without changing the graph language itself.

They define which forms of continuation are allowed in a workflow scope.

### Policy Shape

The implemented workflow-level policy is deliberately small:

```python
from elan import Workflow, WorkflowPolicy

Workflow(
    "dynamic_pipeline",
    start=...,
    result=...,
    policy=WorkflowPolicy(
        max_parallel_tasks=8,
        allow_runtime_expansion=True,
        allow_cycles=False,
    ),
)
```

`max_parallel_tasks` is enforced today. The two `allow_*` fields are declaration
gates: static cycles are rejected unless allowed, while runtime expansion has no
execution mechanism yet.

Future guardrail work may add graph budgets, time budgets, validation
strictness, and finer boundary rules. The previous nested `Policy`,
`BudgetPolicy`, `ValidationPolicy`, and `BoundaryPolicy` sketch is not an
accepted API.

### Default Policy

The current default is equivalent to:

```python
WorkflowPolicy(
    max_parallel_tasks=None,
    allow_runtime_expansion=False,
    allow_cycles=False,
)
```

There are no default graph, recurrence, or time budgets yet.

### Enforcement Model

Elan checks an expansion before materializing it:

- whether it exceeds the current live graph budgets
- whether it exceeds the total graph budgets
- whether it violates a time budget or policy toggle

If any answer is yes, the expansion is rejected before it is appended to the graph.

The handling behavior is part of policy.

Policy controls how Elan reacts when an expansion, cycle step, or task would exceed a budget or violate a boundary rule.

## Relationship To Validation

The guardrails and validation system are related, but not identical.

Validation checks whether the graph and type contracts are valid.

Guardrails constrain what kinds of graph evolution and runtime behavior are allowed.

In practice:

- structural guardrails are enforced through graph validation
- runtime guardrails are enforced through execution policy

## Current Status

The following rules are design requirements for future expansion, not current
runtime behavior:

- append-only materialization
- no rewriting of already materialized nodes or routes
- a fragment declares its entry and owns all of its routes
- the candidate combined graph is validated and appended atomically
- concurrent expansion activations receive isolated run-local identity
- expanded descendants inherit active join-scope membership
- dynamic fragments may reference existing static nodes, but may not mutate them

The current policy surface records whether future runtime expansion would be
allowed, rejects static cycles unless opted into, and lets the scheduler enforce
`max_parallel_tasks`. Expansion itself and safe cycle execution are not
implemented.

The runtime guardrail policy surface still needs a detailed design. Its categories are:

- graph budgets
- time budgets
- expansion policy toggles

Error definitions and handling behavior remain a later topic.

A draft note for that surface lives in
[Error Handling Draft](error_handling_draft.md).
