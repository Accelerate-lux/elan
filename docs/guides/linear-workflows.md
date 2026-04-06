# Linear Workflows

This guide covers the most common Elan topology: a simple linear chain where one node routes directly to the next.

## Smallest linear workflow

```python
from elan import Node, Workflow, task


@task
def prepare():
    return "world"


@task
async def greet(name: str):
    return f"Hello, {name}!"


workflow = Workflow(
    "greet_world",
    start=Node(run=prepare, next="greet"),
    greet=greet,
)

run = await workflow.run()
```

This produces:

```python
{
    "branch-<uuid>": {
        "prepare": ["world"],
        "greet": ["Hello, world!"],
    }
}
```

## Task references by name

Tasks can be referenced by alias or canonical key:

```python
from elan import Node, Workflow, task


@task(alias="prepare")
def build_name():
    return "world"


@task(alias="greet")
async def say_hello(name: str):
    return f"Hello, {name}!"


workflow = Workflow(
    "greet_world",
    start=Node(run="prepare", next="greet_node"),
    greet_node="greet",
)
```

The `run` field uses the global task registry. The `next` field uses workflow-local node names.

## Next steps

- [Data Binding](data-binding.md)
- [Branching](branching.md)
- [Runtime Behavior](../reference/runtime-behavior.md)
