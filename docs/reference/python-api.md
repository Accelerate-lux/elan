# Python API Reference

This page is generated from every name exported by the public `elan` package.
For usage contracts, read [API Overview](api.md) and
[Runtime Behavior](runtime-behavior.md).

!!! info "Capability status"
    `Expand` and `Fragment` are **Experimental**. The remaining exported
    declarations are **Available**. Direct Task invocation and declaration-only
    graph inspection are **Planned**.

## Workflows and results

### `elan.Workflow`

::: elan.Workflow

### `elan.WorkflowRun`

::: elan.WorkflowRun

### `elan.WorkflowPolicy`

::: elan.WorkflowPolicy

## Tasks and graph declarations

### `elan.Task`

::: elan.Task

### `elan.task`

::: elan.task

### `elan.Node`

::: elan.Node

### `elan.When`

::: elan.When

### `elan.Join`

::: elan.Join

### `elan.Expand`

::: elan.Expand

### `elan.Fragment`

::: elan.Fragment

## Binding and references

### `elan.Binder`

::: elan.Binder

### `elan.BindingDict`

::: elan.BindingDict

### `elan.ref`

::: elan.ref

### `elan.Input`

`Input.field` reads a field from the workflow's original keyword input.

### `elan.Upstream`

`Upstream.field` reads a field from the previous node's emitted value.

### `elan.Context`

`Context.field` reads a field from the current branch-local context.

### `elan.Policy`

`Policy.field` reads a field from the immutable runtime policy.
