# Getting Started

This guide walks through one small Elan workflow in detail.

Use it after the homepage example when you want to understand what each part is doing and which forms are recommended first.

```python
import asyncio
from elan import Node, Workflow, task


@task
def prepare():
    return "World"


@task
async def greet(name: str):
    return f"Hello, {name}!"


workflow = Workflow(
    "greet_world",
    start=Node(run=prepare, next="greet"),
    greet=greet,
)

run = asyncio.run(workflow.run())
```

## Step 1: define tasks

`prepare` and `greet` are plain Python functions decorated with `@task`.

That is the basic Elan task model:

- keep business logic in ordinary Python
- keep orchestration outside the task body

!!! note "Recommended"
    Start with plain `@task` functions for business logic. This keeps the logic reusable and easy to test outside the workflow.

## Step 2: define the workflow graph

The workflow says:

- start by running `prepare`
- then route to the node named `greet`

`start=Node(run=prepare, next="greet")` is the first important pattern to learn.

!!! note "Recommended"
    Use `Node(...)` as the normal form once routing matters. It makes the workflow graph explicit and leaves room for binding and branching later.

!!! note "Alternative"
    A bare task is still fine for a trivial single-step workflow or a final step with no routing configuration.

## Step 3: understand how data moves

`prepare()` returns `"World"`.

The next step is `greet(name: str)`, so Elan binds that single scalar output to the single downstream parameter.

This is the default binding behavior for simple linear workflows:

- one scalar output
- one downstream parameter
- no explicit binding configuration needed

## Step 4: inspect the result

After execution, `run.result` is:

```python
"Hello, World!"
```

In this workflow there is no reserved `result` node, so Elan uses the last terminal output as the result because the workflow is linear.

## Step 5: inspect the outputs log

`run.outputs` looks like this:

```python
{
    "branch-<uuid>": {
        "prepare": ["World"],
        "greet": ["Hello, World!"],
    }
}
```

Important points:

- outputs are grouped by branch id first
- then by task name
- each task keeps a list of emitted values

!!! note "Why branch ids appear in a linear workflow"
    Elan uses the same output shape for linear and branched runs. In a linear workflow there is usually just one branch, so you can treat it as the execution path for the run.

!!! note "Do not depend on exact branch id values"
    Branch ids are useful for understanding execution paths, but application code should usually not rely on their literal string values.

## The first recommended path

If you are learning Elan for the first time, prefer this progression:

1. plain `@task` functions
2. `Node(run=..., next="...")` for routing
3. default binding before explicit `bind_input` or `bind_output`
4. linear workflows before branching forms

This gives you the smallest stable mental model before adding branching, structured payloads, or joins.

What you understand now:

- why tasks stay plain Python
- why `Node(...)` is the recommended workflow form once routing matters
- how a simple value flows from one task to the next
- how `run.result` and `run.outputs` differ

Next:

- [Core Concepts](core-concepts.md) for the durable model of `Task`, `Node`, `Workflow`, and `WorkflowRun`
- [Linear Workflows](../guides/linear-workflows.md) for more linear patterns
