# Capability status

This is the canonical maturity ledger for public Elan claims.

| Label | Meaning |
| --- | --- |
| **Available** | Implemented and supported by current documentation and tests. |
| **Experimental** | Implemented and usable, but its API or guardrails may change substantially. |
| **Planned** | Accepted product work that is not implemented. |
| **Direction** | A compatible longer-term intent, not a delivery commitment. |

“Native to the model” is an architectural assessment, not a maturity label. A
capability can be native while still being Experimental, Planned, or Direction.

## Available

- linear workflows and `Workflow` subclass authoring
- typed structured payloads, default binding, `Binder`, and field references
- exclusive routing, conditional routing, fan-out, and yield-driven multiplicity
- workflow-wide and activation-scoped joins
- branch-local workflow context
- workflow composition through explicit result boundaries
- concurrent sibling execution and `WorkflowPolicy.max_parallel_tasks`
- policy validation and static-cycle detection

## Experimental

- append-only runtime graph materialization through typed `Expand` builders and
  self-routed `Fragment` declarations
- fragment-scoped joins
- nested and recursive expansion

Expansion has no built-in depth or total-materialization budget. Recursive
builders must terminate themselves. Candidate validation covers declarations,
tasks, routes, joins, namespaces, result terminality, and cycle policy, but not
complete cross-edge type or reachability analysis.

## Planned

- direct invocation of registered `Task` objects without starting orchestration
- declaration-only graph inspection that does not run tasks or builders
- expansion-depth and total-materialization budgets
- serialization and final materialized-graph inspection
- uniform machine-actionable diagnostic context
- config and HTTP representations using the same workflow semantics
- safe recurrence controls for executable cycles

Planned capabilities have no runnable public syntax. Documentation examples use
only the current API.

## Direction

- persisted runs, retries, resume semantics, timers, and external events
- durable human approval and agent checkpoint boundaries
- remote workers, scheduling, and an optional control plane
- MCP runtime operations after persistent or remote execution exists

## Current distribution and caveats

- Elan is alpha software and may make breaking API changes.
- `elan-workflow` is not published on PyPI; install from the Git repository.
- join contribution order follows runtime arrival order, so reducers should be
  order-agnostic or sort explicitly.
- concurrency is unlimited unless a policy limit is set.
- current exceptions are prose, not a stable structured diagnostic API.
