# Interface Design

This document captures the intended public interface for Elan.

It is a design note. It describes the interface shape Elan is built around, including features that are not implemented yet.

## Public Vocabulary

Elan uses a small top-level vocabulary:

- `Workflow`: orchestration definition
- `task`: registered executable callable
- `Node`: configured use of a task inside a workflow
- `WorkflowRun`: execution of a workflow
- `Context`: scoped execution state declared by the workflow

The split is intentional:

- a task describes work
- a node describes how that work participates in a workflow
- a workflow describes orchestration
- a run is one concrete execution of that workflow
- context carries scoped execution state

## Canonical Python Shape

The smallest workflow is a single task:

```python
import elan as el


@el.task
def hello():
    return "Hello, world!"


workflow = el.Workflow(
    "hello_world",
    start=hello,
)
```

That is the baseline shape Elan should preserve.

## Workflow Context

Context is declared at the workflow level.

It is a pre-declared model, not an open dictionary.

That gives Elan:

- typed execution state
- validated reads and writes
- one stable schema across all branch scopes

Intended shape:

```python
import elan as el
from pydantic import BaseModel


@el.ref
class RunContext(BaseModel):
    user_id: int | None = None
    locale: str = "en"
    surname: str | None = None


workflow = el.Workflow(
    "example",
    context=RunContext,
    start=...,
)
```

Each execution scope carries a value of that model.

When the graph branches, context branches with it. Sibling branches may write the same keys with different values without seeing each other. Join and merge behavior decides what is promoted outside the branch scope.

All context updates follow the same base rule:

- they merge field by field into the current branch scope
- unknown fields are invalid by schema

## Refs

Elan uses registered ref classes for typed field references in the workflow DSL.

`@el.ref` marks a class as referenceable and registers it under a stable id.

That ref concept is used for:

- workflow context model ids
- structured return-model field references in `When(...)`
- structured return-model field references in `After(...)`

Intended shape:

```python
import elan as el
from pydantic import BaseModel


@el.ref
class RoutePayload(BaseModel):
    should_email: bool
    key: str
```

In config and API payloads, the class name is the registry id:

```yaml
context: RunContext
```

and field references serialize as:

```yaml
$RoutePayload.should_email
```

## Nodes

Use a bare task when no extra configuration is needed.

Use a `Node` when the workflow needs to define:

- the next step
- input adaptation
- output adaptation
- context preparation
- post-execution behavior
- routing

The intended `Node` surface is:

- `run`
- `input`
- `context`
- `output`
- `after`
- `next`
- `route_on`

Minimal linear workflow:

```python
import elan as el


@el.task
def normalize_name(name: str):
    return name.strip().title()


@el.task
def greet(name: str):
    return f"Hello, {name}!"


workflow = el.Workflow(
    "greet_world",
    start=el.Node(
        run=normalize_name,
        output="name",
        next="greet",
    ),
    greet=greet,
)
```

## Node Execution Flow

For one node execution, Elan applies these phases in order:

1. `input`: prepare task arguments when the workflow needs to adapt what the task receives
2. `context`: prepare scoped context when the workflow needs to shape the context visible during task execution
3. `run`: execute the task and produce its result
4. `output`: adapt the result when the workflow needs to reshape what the node emits
5. `after`: apply post-execution behavior when the workflow needs small follow-up actions before routing continues
6. `next`: route execution when the workflow continues beyond the current node

These phases are optional. A node only declares the parts it needs.

That keeps the simple case small:

```python
Node(run=hello)
```

and lets complexity appear only when the workflow actually needs it.

This ordering also makes the phase boundaries explicit:

- `input` and `context` are pre-execution
- `output` and `after` are post-execution
- `next` routes the execution that remains after those phases have completed

## Binding and Adaptation

Elan keeps automatic binding narrow.

Automatic binding covers the simple cases:

- scalar output to one downstream parameter
- tuple output to several downstream parameters by position
- structured payloads to downstream named parameters

Plain Python containers stay ordinary Python values:

- raw `list` values are opaque
- raw `dict` values are opaque

When one node interface needs to be reshaped into another, the workflow uses explicit adapters.

## Output Mapping

`Node.output` is the explicit output adapter.

It is used when a node must:

- rename a returned value
- expose only part of a multi-value return
- discard values that should not move forward

Examples:

```python
output="name"
```

turns:

```python
"world"
```

into the named payload:

```python
{"name": "world"}
```

Multi-value output adaptation stays positional:

```python
output=["name", "style"]
output=[..., "style"]
```

In Python, `...` discards a returned position. In config, the equivalent is `null`.

## Input Mapping

`Node.input` is the explicit input adapter.

It is used when a node must consume:

- selected values from the immediate upstream node
- values from the workflow input
- values from the workflow context
- literals

The Python API should use reference objects:

```python
import elan as el
from elan import Context, Input, Upstream


@el.task
def build_profile(name: str, surname: str, locale: str, formal: bool):
    return f"{name} {surname} ({locale}) formal={formal}"


workflow = el.Workflow(
    "profile",
    start=el.Node(
        run=build_profile,
        input={
            "name": Upstream.name,
            "surname": Input.surname,
            "locale": Context.locale,
            "formal": True,
        },
    ),
)
```

The config form should use the serialized reference syntax:

```yaml
input:
  name: $upstream.name
  surname: $input.surname
  locale: $context.locale
  formal: true
```

This keeps the Python API object-based while keeping the config form compact.

The supported sources are:

- `Upstream`
- `Input`
- `Context`
- literals

Arbitrary references to other named nodes are not part of `Node.input`.

That keeps `Node.input` focused on adaptation. Multi-node mixing and join semantics belong to explicit synchronization features, not to ordinary input mapping.

## Context Preparation

`Node.context` prepares the context before the node executes.

It is part of the pre-execution phase, alongside `Node.input`.

That makes one thing explicit: it defines the context view the task sees when it runs.

Intended shape:

```python
import elan as el
from pydantic import BaseModel
from elan import Context, Input, Upstream


@el.ref
class RunContext(BaseModel):
    user_id: int | None = None
    locale: str = "en"
    surname: str | None = None


@el.task
def build_profile(name: str, surname: str, locale: str, formal: bool):
    return f"{name} {surname} ({locale}) formal={formal}"


workflow = el.Workflow(
    "profile",
    context=RunContext,
    start=el.Node(
        run=build_profile,
        input={
            "name": Upstream.name,
            "surname": Input.surname,
            "locale": Context.locale,
            "formal": True,
        },
        context={
            "surname": Input.surname,
        },
    ),
)
```

The `context` field on a node declares the context values that are prepared before task execution.

The config form should use the same reference model:

```yaml
context: RunContext

nodes:
  build_profile:
    run: build_profile
    input:
      name: $upstream.name
      surname: $input.surname
      locale: $context.locale
      formal: true
    context:
      surname: $input.surname
```

Ordinary nodes read freely from context through `Node.input`. `Node.context` prepares scoped context before the task runs.

## After

`after` is the post-execution phase of a node.

It runs after the task has executed and after output adaptation, but before routing continues through `next`.

`after` is the place for small post-execution behaviors that belong to the workflow model.

Intended shape:

```python
import elan as el
from pydantic import BaseModel
from elan import Context, When


@el.ref
class RunContext(BaseModel):
    user_id: int | None = None
    locale: str = "en"
    key: str | None = None


@el.ref
class RoutePayload(BaseModel):
    should_email: bool
    key: str


@el.task
def classify(name: str) -> RoutePayload:
    return RoutePayload(
        should_email=True,
        key="abc123",
    )

workflow = el.Workflow(
    "conditional_routes",
    context=RunContext,
    start=el.Node(
        run=classify,
        after={
            "context": {
                Context.key: RoutePayload.key,
            },
        },
        next=[
            When(RoutePayload.should_email, "send_email"),
        ],
    ),
    send_email=send_email,
)
```

`after` is phase-specific:

- it runs only after successful execution
- it sees the adapted output
- `after.context` may update multiple context keys

The important distinction is that `after` is declarative in the core design. Callback-style hooks are deferred.

## Structured Payloads

Elan supports native structured payloads through Pydantic models.

Pydantic models are the named payload mechanism. Raw dictionaries are not.

That gives Elan one path for validated field binding without making every mapping value behave like workflow syntax.

Example:

```python
import elan as el
from pydantic import BaseModel


@el.ref
class UserPayload(BaseModel):
    name: str
    age: int


@el.task
def build_user() -> UserPayload:
    return UserPayload(name="Ada", age=32)


@el.task
def greet(name: str):
    return f"Hello, {name}!"


workflow = el.Workflow(
    "greet_user",
    start=el.Node(run=build_user, next="greet"),
    greet=greet,
)
```

If the downstream task expects `UserPayload` itself, the model passes through unchanged. Otherwise, its fields bind by name.

## Branching

Branching is any routing form that creates child execution paths.

All branching forms follow the same scope rule:

- each resulting branch gets its own child execution scope
- that child scope inherits the parent scoped context
- sibling branches do not see each other's scoped context updates

The main branching forms are:

- exclusive branching
- conditional multi-routing
- fan-out
- yield-based fan-out

### Exclusive Branching

Exclusive branching uses the `dict` form of `next`.

The workflow declares which output field selects the route through `route_on`.

For simple named outputs, `route_on` may stay a string:

```python
route_on="style"
```

For structured return models, the same intent may also be expressed through registered ref fields:

```python
route_on=RoutePayload.style
```

Intended shape:

```python
import elan as el


@el.task
def choose_greeting(name: str, formal: bool):
    cleaned_name = name.strip().title()
    style = "formal" if formal else "casual"
    return cleaned_name, style


@el.task
def greet_formal(name: str):
    return f"Hello, {name}."


@el.task
def greet_casual(name: str):
    return f"Hey {name}!"


workflow = el.Workflow(
    "branching_greet",
    start=el.Node(
        run=choose_greeting,
        output=["name", "style"],
        route_on="style",
        next={
            "formal": "greet_formal",
            "casual": "greet_casual",
        },
    ),
    greet_formal=greet_formal,
    greet_casual=greet_casual,
)
```

### Conditional Multi-Routing

Conditional multi-routing uses a list of `When(...)` objects in `next`.

This is different from exclusive branching:

- exclusive branching selects one route from a mapping
- conditional multi-routing may activate zero, one, or many downstream nodes

Each `When(...)` is evaluated independently.

Order does not matter.

Zero matches is valid.

Duplicate destinations are allowed.

`When(condition, [...])` is also valid and behaves like conditional fan-out to several destinations.

Intended shape:

```python
import elan as el
from pydantic import BaseModel
from elan import When


@el.ref
class RoutePayload(BaseModel):
    should_email: bool
    should_notify: bool
    should_ticket: bool


@el.task
def classify(name: str) -> RoutePayload:
    return RoutePayload(
        should_email=True,
        should_notify=False,
        should_ticket=True,
    )


workflow = el.Workflow(
    "conditional_routes",
    start=el.Node(
        run=classify,
        next=[
            When(RoutePayload.should_email, "send_email"),
            When(RoutePayload.should_notify, "notify_slack"),
            When(RoutePayload.should_ticket, "open_ticket"),
        ],
    ),
    send_email=send_email,
    notify_slack=notify_slack,
    open_ticket=open_ticket,
)
```

The config form should serialize the same idea explicitly:

```yaml
next:
  - when: $RoutePayload.should_email
    to: send_email
  - when: $RoutePayload.should_notify
    to: notify_slack
  - when: $RoutePayload.should_ticket
    to: open_ticket
  - when: $RoutePayload.should_email
    to:
      - send_email
      - open_ticket
```

### Fan-Out

Fan-out uses the `list` form of `next`.

The current node output is copied to each downstream node.

Intended shape:

```python
import elan as el


@el.task
def prepare_profile(name: str):
    return name.strip().title()


@el.task
def build_greeting(name: str):
    return f"Hello, {name}!"


@el.task
def build_badge(name: str):
    return f"badge:{name.lower()}"


workflow = el.Workflow(
    "fan_out_profile",
    start=el.Node(
        run=prepare_profile,
        output="name",
        next=["build_greeting", "build_badge"],
    ),
    build_greeting=build_greeting,
    build_badge=build_badge,
)
```

### Yield-Based Fan-Out

Yield-based fan-out follows the same routing rules.

Each yielded item is treated like one node output packet and routed independently.

Intended shape:

```python
import elan as el


@el.task
def split_names(names: list[str]):
    for name in names:
        yield name.strip().title()


@el.task
def greet(name: str):
    return f"Hello, {name}!"


workflow = el.Workflow(
    "yield_fan_out",
    start=el.Node(
        run=split_names,
        output="name",
        next="greet",
    ),
    greet=greet,
)
```

## Config Shape

Code, config files, and API payloads should share the same workflow model.

Minimal YAML shape:

```yaml
name: greet_world
context: RunContext
start: normalize
nodes:
  normalize:
    run: normalize_name
    input:
      name: $input.name
    output:
      - name
    next: greet
  greet:
    run: greet
```

The important points are:

- `run` points to a registered task id
- workflow invocation carries an explicit `input` object
- workflows may declare a context model
- nodes may declare `input`, `output`, `context`, `after`, and `next`

Config references should follow the same model as the Python API:

- `$input.foo`
- `$upstream.foo`
- `$context.foo`
- `$context`
- `$RoutePayload.should_email`

Example with both input adaptation and context preparation:

```yaml
name: profile
context: RunContext
start: build_profile
nodes:
  build_profile:
    run: build_profile
    input:
      name: $upstream.name
      surname: $input.surname
      locale: $context.locale
      formal: true
    context:
      surname: $input.surname
```

The design also allows a post-execution phase in config:

```yaml
after:
  context:
    key: $RoutePayload.key
```

## API Shape

The HTTP API should accept the same workflow spec directly.

The API should expose the same workflow model instead of introducing a different orchestration format for HTTP clients.

Suggested endpoints:

- `POST /v1/workflows/runs`
- `GET /v1/workflows/runs/{run_id}`

Minimal create-run request:

```json
{
  "workflow": {
    "name": "hello_world",
    "context": "RunContext",
    "start": "hello",
    "nodes": {
      "hello": {
        "run": "hello"
      }
    }
  },
  "input": {}
}
```

Example create-run request with input adaptation and context preparation:

```json
{
  "workflow": {
    "name": "profile",
    "context": "RunContext",
    "start": "build_profile",
    "nodes": {
      "build_profile": {
        "run": "build_profile",
        "input": {
          "name": "$upstream.name",
          "surname": "$input.surname",
          "locale": "$context.locale",
          "formal": true
        },
        "context": {
          "surname": "$input.surname"
        },
        "after": {
          "context": {
            "key": "$RoutePayload.key"
          }
        }
      }
    }
  },
  "input": {
    "surname": "Lovelace"
  }
}
```

Create-run response:

```json
{
  "run_id": "run_123",
  "status": "accepted"
}
```

Run response:

```json
{
  "run_id": "run_123",
  "workflow": "hello_world",
  "status": "succeeded",
  "output": "Hello, world!"
}
```

The final run response shape still needs to be updated once the execution and result model is fully locked down.

## Later Topics

These topics are part of the broader interface design and should be addressed explicitly later:

- Type system
  - static type validation
  - binding validation
- Dynamic execution
  - dynamic workflows
  - expansion behavior
  - self-writing workflows
  - semi-static runtime validation
  - loop and cycle safety
- Composition
  - sub-workflows
  - branching
  - fan-out
  - barriers and joins
- State
  - scoped context behavior
  - context write authorization
  - merge and promotion rules
- Model surface
  - `After.callback` as an advanced escape hatch
  - whether `after` should later become a dedicated object instead of a plain field
  - the boundary of `after`: whether it should stay limited to context updates or grow to support other post-execution operations
  - explicit edge model
  - workflow run and execution graph shape
  - config and API parity
