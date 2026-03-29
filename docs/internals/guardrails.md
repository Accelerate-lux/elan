# Guardrails

This document captures the guardrails that constrain workflow execution in Elan.

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

### 3. `then` Must Exist When Used

If `Expand(builder, then="node_name")` is used, that `then` target must already exist in the known graph.

`then` is a continuation anchor, not a speculative future reference.

### 4. Returned Structures Are Validated As Currently Materialized

When an expansion builder returns:

- `Node`
- workflow-shaped node fragment
- `Workflow`

Elan validates that structure as it exists now.

If that returned structure itself contains nested `Expand(...)`, Elan validates the current materialized structure now and validates the nested expansion later, when it materializes.

### 5. `Join` Remains Restricted To `result`

Dynamic expansion does not bypass the ordinary graph language.

If a returned structure contains a `Join`, it must still obey the same rule as static workflows:

- `Join` is only allowed as a workflow `result`

### 6. Dynamic Fragments May Reference Existing Static Nodes, But May Not Mutate Them

Returned nodes and fragments may route into already existing static nodes.

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

### Point-In-Time Graph Budgets

These budgets limit how large and complex the graph may be at one moment.

Core examples:

- maximum active branches
- maximum materialized nodes live
- maximum expansion depth

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

- whether a given workflow scope allows `Expand(...)` or callable `next`
- whether nested `Expand(...)` is allowed
- whether recursive dynamic expansion is allowed
- whether direct fragment insertion is allowed
- whether returned `Workflow` expansion is allowed

The workflow-level expansion toggle is especially important because it enables static validation:

- workflows that set `allow_expansion=False` can be checked statically for forbidden dynamic continuation sites
- parent workflows can disable expansion in child scopes without removing dynamic execution globally

This controls graph evolution in sub-workflows without disabling dynamic execution everywhere.

These are not structural rules.

They are policy controls that let users choose how much dynamic power is allowed in a given workflow or runtime environment.

### Enforcement Model

Runtime guardrails are enforced through admission control.

Elan checks an expansion before materializing it:

- whether it exceeds the current live graph budgets
- whether it exceeds the total graph budgets
- whether it violates a time budget or policy toggle

If any answer is yes, the expansion is rejected before it is appended to the graph.

## Relationship To Validation

The guardrails and validation system are related, but not identical.

Validation checks whether the graph and type contracts are valid.

Guardrails constrain what kinds of graph evolution and runtime behavior are allowed.

In practice:

- structural guardrails are enforced through graph validation
- runtime guardrails are enforced through execution policy

## Current Status

The following guardrails are already part of the interface design:

- append-only materialization
- no rewriting of already materialized nodes or routes
- valid current graph after each expansion
- `then` must exist when used
- returned structures are validated as currently materialized
- `Join` remains restricted to `result`
- dynamic fragments may reference existing static nodes, but may not mutate them
- workflows may explicitly disable dynamic expansion in their own scope

The runtime guardrail policy surface still needs a detailed design. Its categories are:

- graph budgets
- time budgets
- expansion policy toggles
