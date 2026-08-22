# Architecture

## Overview

Elan is built around one Python workflow model today, with a design goal of
sharing that model across:

- pure Python workflow definitions
- config-defined workflows
- API-submitted workflow specs

The goal is to keep one coherent execution model rather than separate systems
for code, config, and runtime behavior.

## Public Model

The current public vocabulary is:

- `Workflow`: the workflow definition
- `Task` / `task`: a registered executable callable and decorator
- `Node`: the configured use of a task or workflow inside a graph
- `Join`: workflow-wide or activation-scoped synchronization
- `WorkflowRun`: the result, outputs, and final context of one run
- `WorkflowPolicy`: per-run concurrency and graph-policy controls

This keeps a clear separation between:

- executable implementations
- graph placement and configuration
- workflow definition

## Workflow Shape

At the top level, a workflow is a graph of nodes.

Each node may define:

- what it runs
- how it receives input
- how its outputs are exposed
- where it routes next

The current model is implemented in Python. Planned representations include:

- Python
- YAML
- JSON
- TOML
- HTTP API payloads

## Inputs and Outputs

Tasks use normal Python parameters and may return freeform Python values.

Workflow-level input and output behavior is defined by the graph model:

- workflow runs receive an initial input object
- node input mapping may bind from workflow input or prior node output
- node output mapping unpacks return values into named fields
- Python uses `...` as the discard marker in output mappings
- a future config representation may use `null` as the discard marker

Automatic binding is the default in pure Python when the previous node output
matches the next node signature cleanly.

## Control Flow

Control flow is expressed through `next`.

The same field supports:

- `str` for linear flow
- `list` for fan-out
- `dict` for conditional routing

Conditional routing remains part of the workflow model rather than being hidden
inside task output conventions.

When routing depends on node output, the workflow may declare `route_on` to say
which named output field selects the route.

## Dynamic Execution

Elan treats dynamic graph behavior as part of the core model.

Implemented dynamic-cardinality behavior includes:

- branching
- fan-out
- yield-based fan-out

Planned graph-evolution behavior includes:

- graph expansion during execution
- cycles and recurrence

Static-cycle detection and a policy opt-in exist today. Safe executable
recurrence still requires runtime safeguards and budgets; loops are not yet a
supported production feature.

## Synchronization

Synchronization is centered on workflow scopes.

Synchronization is represented directly by `Join`. A workflow-wide result join
waits for the workflow to become quiescent. A mid-graph join names a scope node,
and each activation of that node creates an isolated barrier for its descendant
branch family.

This means:

- sub-workflow completion provides implicit synchronization
- workflow-wide joins collect explicitly routed terminal contributions
- activation-scoped joins can reduce and continue in the middle of a graph

## Design Direction

The design stays centered on a small number of consistent primitives.

The intent is to let simple workflows stay simple, while allowing implemented
behavior such as branching, fan-out, scoped barriers, and composition to share
the same model. Runtime graph expansion and guarded recurrence remain future
directions.
