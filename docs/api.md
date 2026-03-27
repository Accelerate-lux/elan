# API

This document is a compact reference for the Elan public API.

For an introduction to the model, see [Basics](basics.md).

## `@task`

Registers a callable as an Elan task and returns a `Task` object.

```python
from elan import task

@task
def hello():
    return "Hello, world!"
```

The decorator also supports an explicit alias:

```python
@task(alias="bonjour")
def hello():
    return "Hello, world!"
```

## `Task`

Public task definition object returned by `@task`.

Task metadata includes:

- canonical key
- optional alias
- display name
- underlying callable
- signature metadata
- async/sync mode

## Structured Payloads

Elan supports native structured payloads through Pydantic models.

When a task returns a Pydantic model:

- Elan validates it natively
- the next task may receive it as one value if it expects that model type
- otherwise Elan may bind matching model fields by name

Raw `dict` values are not treated as structured payloads. They remain opaque values unless a node explicitly adapts them.

## `Workflow(name, start, **nodes)`

Defines a workflow.

Parameters:

- `name: str`
- `start: Task | str | Node`
- `**nodes: Task | str | Node`

String task references are resolved through the task registry.

## `await workflow.run(**input)`

Runs the workflow and returns a `WorkflowRun`.

## `Node(run, next=None, input=None, output=None, route_on=None)`

Defines a configured task node.

Supported fields:

- `run: Task | str`
- `next` as `str`
- `output`

Declared but unsupported fields:

- `input`
- `route_on`

## `WorkflowRun`

Fields:

- `result: dict[str, list[Any]]`

## Binding Rules

`Workflow.run(**input)` binds named workflow input to the start task.

Between nodes, Elan binds values using these rules:

- scalar outputs may bind to one downstream parameter
- tuple outputs may bind positionally to a fixed downstream signature
- list outputs remain opaque values
- raw `dict` outputs remain opaque values
- Pydantic model outputs may pass through as one value or auto-unpack by field name
- explicit `Node.output` mapping creates a named adapter payload for downstream binding
