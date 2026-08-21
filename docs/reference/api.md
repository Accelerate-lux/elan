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
- `bind_context: Binder[ContextModel] | dict[str, Any] | None`
- `policy: WorkflowPolicy | None`
- public node attributes with values of type `Task | str | Workflow | Node | Join`

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

Application workflow subclasses may override `run(...)` to expose a real Python
signature. Custom `run(...)` methods should call `await self._run(...)`, which is
the protected runtime entrypoint.

```python
class GreetingWorkflow(Workflow):
    start = greet

    async def run(self, *, name: str = "world"):
        return await self._run(name=name)
```

## `Workflow(name, start, context=None, bind_context=None, policy=None, **nodes)`

Programmatic and inline authoring form. This remains supported for tests,
small examples, REPL use, and generated graphs.

Parameters:

- `name: str`
- `start: Task | str | Workflow | Node`
- `context: type[BaseModel] | None`
- `bind_context: Binder[ContextModel] | dict[str, Any] | None`
- `policy: WorkflowPolicy | None`
- `**nodes: Task | str | Workflow | Node | Join`

## `WorkflowPolicy`

Runtime governance object for execution-shape limits.

Built-in fields:

- `max_parallel_tasks: int | None = None`
- `allow_runtime_expansion: bool = False`
- `allow_cycles: bool = False`

Policy is immutable for a run and is declared as an object, not bound from
workflow input. Child workflows inherit the parent policy unless they declare a
narrower policy. Narrowing is accepted when `parent_policy.allows(child_policy)`
returns `True`.

## `Binder[target](...)`

Typed binding dictionary for explicit binding declarations.

```python
class ReviewContext(BaseModel):
    locale: str
    reviewer: str


class ReviewWorkflow(Workflow):
    policy = WorkflowPolicy(max_parallel_tasks=4)
    context = ReviewContext
    bind_context = Binder[ReviewContext](
        locale=Input.locale,
        reviewer="default",
    )
    start = Node(run=review)
```

```python
@task
def greet(name: str, punctuation: str):
    return f"Hello, {name}{punctuation}"


greet_node = Node(
    run=greet,
    bind_input=Binder[greet](punctuation="!"),
)
```

Supported targets:

- `Binder[ContextModel]` for `Workflow.bind_context` and `Node.context`
- `Binder[task_or_callable]` for `Node.bind_input`

`Binder[...]` validates binding keys when the object is created. It remains
a normal dictionary at runtime, so raw dictionaries continue to work for compact
examples and programmatic graph construction.

## `Input`, `Context`, `Policy`, and `Upstream`

Reference namespaces for explicit bindings.

- `Input.field` reads workflow input
- `Context.field` reads current branch context
- `Policy.field` reads immutable run policy
- `Upstream.field` reads the previous node's emitted value

## `await workflow.run(**input)` and `await workflow._run(**input)`

`run(...)` is the public callable interface. The base implementation accepts
arbitrary keyword input for constructor-authored workflows.

`_run(...)` is the protected runtime entrypoint. Subclasses that override
`run(...)` for a typed Python signature should delegate to `_run(...)`.

## `Node(run, next=None, bind_input=None, bind_output=None, context=None, route_on=None)`

Defines a configured task node.

Supported fields:

- `run: Task | str | Workflow`
- `next` as `str | list[str | When] | dict[str, str]`
- `bind_input: Binder[task] | dict[str, Any] | None`
- `bind_output`
- `context: Binder[ContextModel] | dict[str, Any] | None`
- `route_on`

## `When(condition, target)`

Conditional routing primitive used inside `Node.next`.

Supported forms include:

- `When("should_email", "send_email")`
- `When(RoutePayload.should_email, "send_email")`
- `When("should_ticket", ["open_ticket", "audit"])`

## `Join(run=None, scope=None, next=None, bind_output=None, route_on=None)`

Synchronization and reduction primitive.

Supported forms:

- `result=Join()`
- `result=Join(run=reduce_values)`
- `result=Join(run=reduce_values, scope="start")`
- `merged=Join(run=reduce_values, scope="fan_out", next="continue")`

Outside the reserved `result` node, `scope` is required. Each activation of the
declared scope creates an independent barrier. Descendant branches are awaited;
only branches explicitly routed to the join contribute values.

The reducer runs on the scope owner's branch and may receive the workflow context
through normal typed injection. Its raw return is recorded in `WorkflowRun.outputs`.
`bind_output`, `route_on`, and `next` then behave as they do for `Node` output.
Sibling branch contexts remain isolated and are not merged automatically.

`result=Join(...)` remains terminal. Without `scope`, it waits for the whole
workflow. With `scope`, that scope must activate exactly once.

## `WorkflowRun`

Completed runs expose both `result` and the final committed `context`. Child
workflows commit this context to their parent branch before parent execution
continues.

Fields:

- `result: Any`
- `outputs: dict[str, dict[str, list[Any]]]`
- `context: BaseModel | None`

## Reference pages

For detailed behavior, see:

- [Runtime Behavior](runtime-behavior.md)
- [Python API](python-api.md)
