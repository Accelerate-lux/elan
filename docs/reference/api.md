# API Overview

This page is the compact handwritten reference for the Elan public surface.

For generated object-level API docs, see [Python API](python-api.md).

## `@task`

Registers a callable as an Elan task and returns a `Task` object.

Tasks may be ordinary functions, async functions, sync generators, or async generators.
Generator tasks perform yield-based fan-out: each yielded item is routed through
the task node's `next` value independently.

The decorator also supports an explicit alias:

```python
@task(alias="bonjour")
def hello():
    return "Hello, world!"
```

## `@ref`

Registers a Pydantic model class for field-reference features.

Ordinary Pydantic binding does not require `@ref`.

## `class MyWorkflow(Workflow)`

Preferred authoring form for application workflows.

```python
class GreetingWorkflow(Workflow):
    start = Node(run=prepare_name, next="greet")
    greet = greet_name
```

Supported class declarations:

- `name: str`
- `start: Task | str | Node`
- `context: type[BaseModel] | None`
- `bind_context: dict[str, Any] | None`
- public node attributes with values of type `Task | str | Node | Join`

If `name` is omitted, the workflow name defaults to the class name.
Subclass attributes override inherited declarations.

Instantiate the subclass to validate and build the runnable workflow object:

```python
workflow = GreetingWorkflow()
```

## `Workflow(name, start, context=None, bind_context=None, **nodes)`

Programmatic and inline authoring form. This remains supported for tests,
small examples, REPL use, and generated graphs.

Parameters:

- `name: str`
- `start: Task | str | Node`
- `context: type[BaseModel] | None`
- `bind_context: dict[str, Any] | None`
- `**nodes: Task | str | Node | Join`

## `await workflow.run(**input)`

Runs the workflow and returns a `WorkflowRun`.

## `Node(run, next=None, bind_input=None, bind_output=None, context=None, route_on=None)`

Defines a configured task node.

Supported fields:

- `run: Task | str`
- `next` as `str | list[str | When] | dict[str, str]`
- `bind_input`
- `bind_output`
- `context`
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
