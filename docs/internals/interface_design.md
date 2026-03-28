# Interface Design

This document captures the intended public interface for Elan.

It is a design note. It describes the interface shape Elan is built around, including features that are not implemented yet.

## Public Vocabulary

Elan uses a small top-level vocabulary:

- `Workflow`: orchestration definition
- `task`: registered executable callable
- `Node`: configured use of a task inside a workflow
- `WorkflowRun`: execution of a workflow

The split is intentional:

- a task describes work
- a node describes how that work participates in a workflow
- a workflow describes orchestration
- a run is one concrete execution of that workflow

## Canonical Python Shape

The smallest workflow is a single task:

```python
from elan import Workflow, task


@task
def hello():
    return "Hello, world!"


workflow = Workflow(
    "hello_world",
    start=hello,
)
```

That is the baseline shape Elan should preserve.

## Nodes

Use a bare task when no extra configuration is needed.

Use a `Node` when the workflow needs to define:

- the next step
- input adaptation
- output adaptation
- routing

Minimal linear workflow:

```python
from elan import Node, Workflow, task


@task
def normalize_name(name: str):
    return name.strip().title()


@task
def greet(name: str):
    return f"Hello, {name}!"


workflow = Workflow(
    "greet_world",
    start=Node(
        run=normalize_name,
        output="name",
        next="greet",
    ),
    greet=greet,
)
```

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
from elan import Context, Input, Node, Upstream, Workflow, task


@task
def build_profile(name: str, surname: str, locale: str, formal: bool):
    return f"{name} {surname} ({locale}) formal={formal}"


workflow = Workflow(
    "profile",
    start=Node(
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

## Structured Payloads

Elan supports native structured payloads through Pydantic models.

Pydantic models are the named payload mechanism. Raw dictionaries are not.

That gives Elan one path for validated field binding without making every mapping value behave like workflow syntax.

Example:

```python
from pydantic import BaseModel
from elan import Node, Workflow, task


class UserPayload(BaseModel):
    name: str
    age: int


@task
def build_user() -> UserPayload:
    return UserPayload(name="Ada", age=32)


@task
def greet(name: str):
    return f"Hello, {name}!"


workflow = Workflow(
    "greet_user",
    start=Node(run=build_user, next="greet"),
    greet=greet,
)
```

If the downstream task expects `UserPayload` itself, the model passes through unchanged. Otherwise, its fields bind by name.

## Branching

Branching uses the `dict` form of `next`.

The workflow declares which output field selects the route through `route_on`.

Intended shape:

```python
from elan import Node, Workflow, task


@task
def choose_greeting(name: str, formal: bool):
    cleaned_name = name.strip().title()
    style = "formal" if formal else "casual"
    return cleaned_name, style


@task
def greet_formal(name: str):
    return f"Hello, {name}."


@task
def greet_casual(name: str):
    return f"Hey {name}!"


workflow = Workflow(
    "branching_greet",
    start=Node(
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

## Fan-Out

Fan-out uses the `list` form of `next`.

The current node output is copied to each downstream node.

Intended shape:

```python
from elan import Node, Workflow, task


@task
def prepare_profile(name: str):
    return name.strip().title()


@task
def build_greeting(name: str):
    return f"Hello, {name}!"


@task
def build_badge(name: str):
    return f"badge:{name.lower()}"


workflow = Workflow(
    "fan_out_profile",
    start=Node(
        run=prepare_profile,
        output="name",
        next=["build_greeting", "build_badge"],
    ),
    build_greeting=build_greeting,
    build_badge=build_badge,
)
```

## Yield-Based Fan-Out

Yield-based fan-out follows the same routing rules.

Each yielded item is treated like one node output packet and routed independently.

Intended shape:

```python
from elan import Node, Workflow, task


@task
def split_names(names: list[str]):
    for name in names:
        yield name.strip().title()


@task
def greet(name: str):
    return f"Hello, {name}!"


workflow = Workflow(
    "yield_fan_out",
    start=Node(
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
- nodes may declare `input`, `output`, and `next`

## API Shape

The HTTP API should accept the same workflow spec directly.

Intended minimal create-run request:

```json
{
  "workflow": {
    "name": "hello_world",
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

Intended create-run response:

```json
{
  "run_id": "run_123",
  "status": "accepted"
}
```

Intended run response:

```json
{
  "run_id": "run_123",
  "workflow": "hello_world",
  "status": "succeeded",
  "output": "Hello, world!"
}
```
