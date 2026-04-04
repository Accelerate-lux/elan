# API Overview

This page is the compact handwritten reference for the Elan public surface.

For generated object-level API docs, see [Python API](python-api.md).

## `@task`

Registers a callable as an Elan task and returns a `Task` object.

The decorator also supports an explicit alias:

```python
@task(alias="bonjour")
def hello():
    return "Hello, world!"
```

## `@ref`

Registers a Pydantic model class for field-reference features.

Ordinary Pydantic binding does not require `@ref`.

## `Workflow(name, start, context=None, **nodes)`

Defines a workflow.

Parameters:

- `name: str`
- `start: Task | str | Node`
- `context: type[BaseModel] | None`
- `**nodes: Task | str | Node | Join`

## `await workflow.run(**input)`

Runs the workflow and returns a `WorkflowRun`.

## `Node(run, next=None, bind_input=None, bind_output=None, route_on=None)`

Defines a configured task node.

Supported fields:

- `run: Task | str`
- `next` as `str | list[str | When] | dict[str, str]`
- `bind_input`
- `bind_output`
- `route_on`

## `When(condition, target)`

Conditional routing primitive used inside `Node.next`.

Supported forms include:

- `When("should_email", "send_email")`
- `When(RoutePayload.should_email, "send_email")`
- `When("should_ticket", ["open_ticket", "audit"])`

## `Join(run=None)`

Terminal workflow-scope synchronization primitive.

Supported forms:

- `result=Join()`
- `result=Join(run=reduce_values)`

`Join` is only valid as the reserved `result` node.

## `WorkflowRun`

Fields:

- `result: Any`
- `outputs: dict[str, dict[str, list[Any]]]`

## Reference pages

For detailed behavior, see:

- [Runtime Behavior](runtime-behavior.md)
- [Python API](python-api.md)
