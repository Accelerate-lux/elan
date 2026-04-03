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

`@ref` is only required when you want to use explicit field-reference features. Ordinary Pydantic binding does not require registration.

## `@ref`

Registers a Pydantic model class for field-reference features.

```python
from pydantic import BaseModel
from elan import ref


@ref
class UserPayload(BaseModel):
    name: str
    age: int
```

## `Upstream`, `Input`, and `Context`

Reference namespaces used by `Node.bind_input`.

Examples:

```python
from elan import Context, Input, Node, Upstream

Node(
    run=greet,
    bind_input={
        "name": Upstream.name,
        "title": Input.title,
        "punctuation": Context.punctuation,
    },
)
```

## `Workflow(name, start, context=None, **nodes)`

Defines a workflow.

Parameters:

- `name: str`
- `start: Task | str | Node`
- `context: type[BaseModel] | None`
- `**nodes: Task | str | Node`

String task references are resolved through the task registry.

## `await workflow.run(**input)`

Runs the workflow and returns a `WorkflowRun`.

## `Node(run, next=None, bind_input=None, bind_output=None, route_on=None)`

Defines a configured task node.

Supported fields:

- `run: Task | str`
- `next` as `str`
- `bind_input`
- `bind_output`

Declared but unsupported fields:

- `route_on`

## `WorkflowRun`

Fields:

- `result: Any`
- `outputs: dict[str, list[Any]]`

## Binding Rules

`Workflow.run(**input)` binds named workflow input to the start task.

`WorkflowRun.result` is the exported value of the reserved `result` node when the workflow defines one.

If no reserved `result` node is defined, `WorkflowRun.result` falls back to the last terminal output of the run.

`WorkflowRun.outputs` stores executed task outputs grouped by task name.

Between nodes, Elan binds values using these rules:

- scalar outputs may bind to one downstream parameter
- tuple outputs may bind positionally to a fixed downstream signature
- list outputs remain opaque values
- raw `dict` outputs remain opaque values
- Pydantic model outputs may pass through as one value or auto-unpack by field name
- explicit `Node.bind_output` mapping creates a named adapter payload for downstream binding
- `Node.bind_input` may provide explicit literal values for target parameters
- `Node.bind_input` may also read from `Upstream.field`, `Input.field`, and `Context.field`
