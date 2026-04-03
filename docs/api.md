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

## `When(condition, target)`

Conditional routing primitive used inside `Node.next`.

Supported forms:

- `When("should_email", "send_email")`
- `When(RoutePayload.should_email, "send_email")`
- `When("should_ticket", ["open_ticket", "audit"])`

## `Join(run=None)`

Terminal workflow-scope synchronization primitive.

Supported forms:

- `result=Join()`
- `result=Join(run=reduce_values)`

`Join` is only valid as the reserved `result` node.

## `Workflow(name, start, context=None, **nodes)`

Defines a workflow.

Parameters:

- `name: str`
- `start: Task | str | Node`
- `context: type[BaseModel] | None`
- `**nodes: Task | str | Node | Join`

String task references are resolved through the task registry.

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

## `WorkflowRun`

Fields:

- `result: Any`
- `outputs: dict[str, dict[str, list[Any]]]`

## Binding Rules

`Workflow.run(**input)` binds named workflow input to the start task.

`WorkflowRun.result` is the exported value of the reserved `result` node when the workflow defines one.

If no reserved `result` node is defined, `WorkflowRun.result` falls back to the last terminal output of the run.

`WorkflowRun.outputs` stores executed task outputs grouped first by branch id, then by task name.

For linear runs, the shape still uses the initial branch id:

```python
{
    "branch-1": {
        "prepare": ["world"],
        "greet": ["Hello, world!"],
    }
}
```

For branched runs, sibling outputs are separated by branch id:

```python
{
    "branch-1": {
        "prepare": ["world"],
    },
    "branch-2": {
        "greet": ["Hello, world!"],
    },
    "branch-3": {
        "badge": ["badge:world"],
    },
}
```

Between nodes, Elan binds values using these rules:

- scalar outputs may bind to one downstream parameter
- tuple outputs may bind positionally to a fixed downstream signature
- list outputs remain opaque values
- raw `dict` outputs remain opaque values
- Pydantic model outputs may pass through as one value or auto-unpack by field name
- explicit `Node.bind_output` mapping creates a named adapter payload for downstream binding
- `Node.bind_input` may provide explicit literal values for target parameters
- `Node.bind_input` may also read from `Upstream.field`, `Input.field`, and `Context.field`

## Branching Rules

The current runtime supports three branching forms:

- `next={"formal": "greet_formal", "casual": "greet_casual"}` with `route_on="style"`
- `next={"formal": "greet_formal", "casual": "greet_casual"}` with `route_on=RoutePayload.style`
- `next=["a", "b"]` for fan-out
- `next=[When("should_email", "send_email"), When(RoutePayload.should_ticket, ["open_ticket", "audit"])]`

Inside `next=[...]`, plain node ids and `When(...)` entries may be mixed. The list is evaluated left to right as a sequence of target producers.

For mapping-based branching, Elan reads the route selector from:

- named adapter payloads created by `bind_output` when `route_on` is a string
- raw `dict` outputs when `route_on` is a string
- registered `@ref` model outputs when `route_on` is a ref field like `RoutePayload.style`

For `When(...)`:

- string conditions read from named adapter payloads and raw `dict` outputs
- ref-field conditions read from registered `@ref` model instances only
- conditions must resolve to `bool`

Ref-based `route_on` currently applies to exclusive branching with `next={...}` only.

If a workflow uses branching forms and does not define the reserved `result` node, `WorkflowRun.result` is `None`.

If `result=Join(...)` is used:

- branches routed to `result` contribute their emitted values
- non-contributing branches are still awaited
- `Join()` returns the collected list
- `Join(run=reducer)` calls the reducer with the collected list as one value
- join reduction is not recorded in `WorkflowRun.outputs`
