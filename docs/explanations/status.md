# Status

This page summarizes the current public implementation status of Elan.

## Implemented today

- linear workflows
- `Workflow` subclass authoring
- `bind_output`
- `bind_input`
- structured payload binding
- `@ref` field-reference features
- exclusive branching
- fan-out
- yield-based fan-out
- `When(...)`
- terminal `Join` on reserved `result`
- concurrent execution of sibling runnable branches

## Not implemented yet

- workflow composition
- dynamic expansion
- callable continuation growth
- cycles and broader dynamic graph materialization
- mid-graph joins and general barriers
- post-execution workflow hooks or context update phases

## Current behavioral caveats

- join contribution order follows runtime arrival order
- reducers should be order-agnostic unless completion timing is intentionally constrained
- scheduler concurrency is currently unlimited

## How to read the docs today

- use **Learn** for the first mental model
- use **Guides** for task-oriented workflows
- use **Reference** for exact behavior
- use **Comparisons** for product positioning against adjacent tools
