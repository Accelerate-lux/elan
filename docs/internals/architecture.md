# Architecture

## Overview

Elan is built around a single workflow model shared across:

- pure Python workflow definitions
- config-defined workflows
- API-submitted workflow specs

The goal is to keep one coherent execution model rather than separate systems
for code, config, and runtime behavior.

## Public Model

The current public vocabulary is:

- `Workflow`: the workflow definition
- `task`: a registered executable callable
- `Node`: the configured use of a task or workflow inside a graph
- `run`: the execution of a workflow

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

The same model is representable in:

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
- config formats use `null` as the discard marker

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

This includes:

- branching
- fan-out
- yield-based fan-out
- graph expansion during execution
- cycles and recurrence

Loops are not a separate primitive at the core level. A loop is a cycle in the
graph, and cycle safety is handled through runtime safeguards rather than a
separate syntax.

## Synchronization

Synchronization is centered on workflow scopes.

In the dynamic case, a barrier is effectively a workflow wrapper with join
semantics. The meaningful thing to wait on is not a flat list of descendant
tasks, but the completion of a branch or sub-workflow scope.

This means:

- sub-workflow completion provides implicit synchronization
- explicit barrier behavior is still possible when synchronization needs to be
  represented directly in the graph

## Design Direction

The design stays centered on a small number of consistent primitives.

The intent is to let simple workflows stay simple, while allowing more advanced
behavior such as branching, fan-out, recursive barriers, and dynamic graph
expansion to emerge from the same underlying model.
