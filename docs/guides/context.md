# Context

This guide will cover workflow context, node context access, and later context updates through `after`.

## Current state

Elan currently supports:

- declaring a workflow context model
- creating a fresh context instance per run
- reading context fields through `Context.field` in `Node.bind_input`

Elan does not yet support the broader mutable context workflow described in the roadmap.

## Planned coverage

This page will eventually document:

- defining context models
- reading context in tasks and bindings
- branch-local context semantics
- post-execution updates through `after`

## For now

See:

- [Data Binding](data-binding.md)
- [Runtime Behavior](../reference/runtime-behavior.md)
