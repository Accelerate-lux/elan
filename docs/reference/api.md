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
    greet: Node

    start = Node(run=prepare_name, next=greet)
    greet = Node(run=greet_name)
```

Supported class declarations:

- `name: str`
- `start: Task | str | Node`
- `context: type[BaseModel] | None`
- `bind_context: dict[str, Any] | None`
- public node attributes with values of type `Task | str | Node | Join`

If `name` is omitted, the workflow name defaults to the class name.
Subclass attributes override inherited declarations.

Annotation-only class attributes such as `greet: Node` or `result: Join` may be
used as forward declarations. Within `Workflow` subclasses, those names can be
used anywhere a `next` target is expected, including lists, `When(...)` targets,
and route mappings.

Because these names are resolved by the `Workflow` subclass authoring runtime,
static linters do not see them as normal Python assignments. If you use
forward-declared node references, keep the workflow declaration in a dedicated
module and use file-level Ruff `F821` suppression:

```python
# ruff: noqa: F821

class GreetingWorkflow(Workflow):
    greet: Node
    result: Join

    start = Node(run=prepare_name, next=greet)
    greet = Node(run=greet_name, next=result)
    result = Join()
```

For larger application workflows, prefer one workflow class per file. Keep task
functions, models, and helper constants above the class or import them from
nearby modules. That makes the intentional workflow-DSL section obvious and
keeps the file-level lint suppression honest. If a workflow must live in a mixed
module, use a narrower `# ruff: disable[F821]` / `# ruff: enable[F821]` block
around the wiring section instead.

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
