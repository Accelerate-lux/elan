# API

This document is a compact reference for the Elan public API.

For an introduction to the model, see [Basics](basics.md).

## `@task`

Registers a callable so it can be executed by a workflow.

```python
from elan import task

@task
def hello():
    return "Hello, world!"
```

## `Workflow(name, start, **nodes)`

Defines a workflow.

Parameters:

- `name: str`
- `start: task | Node`
- `**nodes: task | Node`

## `await workflow.run(**input)`

Runs the workflow and returns a `WorkflowRun`.

## `Node(run, next=None, input=None, output=None, route_on=None)`

Defines a configured task node.

Supported fields:

- `run`
- `next` as `str`
- `output`

Declared but unsupported fields:

- `input`
- `route_on`

## `WorkflowRun`

Fields:

- `result: dict[str, list[Any]]`
