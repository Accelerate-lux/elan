# Data Binding

This guide explains how values move from one node to the next.

The core rule is:

- fixed-shape outputs move positionally
- structured payloads can bind by field name
- plain Python containers stay opaque unless explicitly adapted

## Workflow entrypoint binding

`workflow.run(**kwargs)` binds named input directly to the start task.

```python
from elan import Workflow, task


@task
async def greet(name: str):
    return f"Hello, {name}!"


workflow = Workflow("hello_world", start=greet)
run = await workflow.run(name="world")
```

## Scalar and tuple binding

Scalars bind to one downstream parameter:

```python
@task
def prepare():
    return "world"
```

Tuples bind positionally to fixed downstream signatures:

```python
@task
def prepare():
    return "hello", "world"
```

## Opaque containers

Lists and raw dictionaries remain opaque and are passed as one value.

```python
@task
def prepare():
    return {"name": "world"}
```

## Structured payloads

Pydantic models are treated as structured payloads:

- they may pass through as one value if the downstream task expects that model
- otherwise Elan may bind matching fields by name

`@ref` is only required for field-reference features. Ordinary Pydantic binding still works without it.

## `bind_output`

Use `bind_output` to reshape a task output before it moves downstream.

```python
workflow = Workflow(
    "greet_world",
    start=Node(run=prepare, bind_output="name", next="greet"),
    greet=greet,
)
```

Supported baseline forms:

- `bind_output="name"`
- `bind_output=["name", "style"]`
- `bind_output=[..., "style"]`

## `bind_input`

Use `bind_input` to prepare explicit downstream inputs.

Literal example:

```python
greet=Node(run=greet, bind_input={"punctuation": "!"})
```

Reference example:

```python
bind_input={
    "name": Upstream.name,
    "title": Input.title,
    "punctuation": Context.punctuation,
}
```

Current supported sources:

- literal values
- `Upstream.field`
- `Input.field`
- `Context.field`

## Next steps

- [Branching](branching.md)
- [API Overview](../reference/api.md)
- [Runtime Behavior](../reference/runtime-behavior.md)
