# Getting Started

This guide will show you how to define a small Elan workflow, pass input into it, follow how data moves from one task to the next, and read the final result and execution outputs.

By the end of this guide, you will understand:

- How to define reusable tasks using plain Python functions.
- How to connect those tasks together into a workflow graph.
- How to pass inputs into the workflow execution.
- How data flows between tasks using auto-unpacking and type hints.
- How to access the final workflow result and inspect the complete execution log.

```python
import asyncio
import re
from pydantic import BaseModel
from elan import Node, Workflow, task


class ArticleDraft(BaseModel):
    title: str
    slug: str
    author: str


@task
def prepare_article(title: str, author: str) -> ArticleDraft:
    normalized_title = title.strip()
    normalized_author = author.strip()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized_title.lower()).strip("-")
    return ArticleDraft(
        title=normalized_title,
        slug=slug,
        author=normalized_author,
    )


@task
async def publish_article(slug: str):
    return f"/articles/{slug}"


@task
def build_notification(url: str):
    return f"Article ready at {url}"


workflow = Workflow(
    "publish_article",
    start=Node(run=prepare_article, next="publish"),
    publish=Node(run=publish_article, next="notify"),
    notify=build_notification,
)

run = asyncio.run(
    workflow.run(
        title="  Launching Elan 0.1  ",
        author=" Hugo ",
    )
)
```

## Step 1: define tasks

We define the business logic in plain Python functions `prepare_article`, `publish_article`, and `build_notification` and decorate them with `@task` to make them discoverable by Elan.

This lets us keep the business logic pure, reusable, and decoupled from the orchestration defined in the workflow.

## Step 2: define the workflow graph

Workflows are defined by creating a `Workflow` object and passing it a set of `Nodes` as keyword arguments. The keyword arguments passed to the workflow define the node names, and Elan uses those names to resolve the graph edges. Some keywords, like `start` are reserved for specific Nodes in the workflow.

A workflow instance represents an execution graph definition and can be run multiple times. 

We use the `start=` keyword to define the workflow entrypoint, so Elan begins execution at `prepare_article`.

We then pass the `publish` and `notify` keyword arguments to define the downstream nodes.

And we route each Node's output to the next usein the `next` attribute of the `Node`class:

- `Node(run=prepare_article, next="publish")` tells Elan to run `prepare_article` and then route its output to `publish`.
- `Node(run=publish_article, next="notify")` tells Elan to run `publish_article` and then route its output to `notify`.

## Step 3: pass input into the workflow

The workflow is executed with:

```python
workflow.run(
    title="  Launching Elan 0.1  ",
    author=" Hugo ",
)
```

Elan binds those named inputs to the start task, so `prepare_article(title: str, author: str)` receives them directly.

## Step 4: understand how data moves

By default, Elan passes the output of a task to the next as-is, leaving the responsibility of compatibility to the user. However, because Elan's graph definition syntax does not allow custom mapping logic between tasks (like `**values`), this could force you to pass full objects and pollute your task's business logic with data extraction code.

To solve this and facilitate composability, Elan uses **auto-unpacking**. When an upstream task returns a structured model (like our `ArticleDraft` Pydantic model):

```python
ArticleDraft(
    title="Launching Elan 0.1",
    slug="launching-elan-0-1",
    author="Hugo",
)
```

Elan can automatically unpack its fields for downstream tasks. This behavior is controlled by type hinting:

- **Auto-unpacking:** If the downstream task expects specific fields (e.g., `def publish_article(slug: str):`), Elan automatically unpacks the matching `slug` field from the `ArticleDraft`.
- **As-is passing:** If the downstream task expects the full model (e.g., `def publish_article(draft: ArticleDraft):`), Elan skips unpacking and passes the whole object.

This allows upstream tasks to return meaningful models once, while downstream tasks consume only the fields they need directly.

## Step 5: inspect the result

After execution, `run.result` contains the final output of our workflow:

```python
"Article ready at /articles/launching-elan-0-1"
```

Because we didn't explicitly define a reserved `result` node, Elan automatically falls back to using the output of the last terminal node (`notify` in this case). This makes simple, linear workflows work out of the box without extra boilerplate.

## Step 6: inspect the outputs log

While `run.result` gives you the final answer, `run.outputs` provides a complete log of everything that happened during execution:

```python
{
    "branch-<uuid>": {
        "prepare_article": [
            ArticleDraft(
                title="Launching Elan 0.1",
                slug="launching-elan-0-1",
                author="Hugo",
            )
        ],
        "publish": ["/articles/launching-elan-0-1"],
        "notify": ["Article ready at /articles/launching-elan-0-1"],
    }
}
```

Notice how the data is structured:

- **Grouped by branch:** Even in a simple linear workflow, Elan groups outputs by an internal "branch ID". This ensures the output shape remains consistent whether your workflow is a straight line or a complex, multi-branching graph.
- **Lists of values:** Each task stores its emitted values in a list. Even if a task only runs once, Elan uses lists to accommodate tasks that might be called multiple times in loops or branches.

!!! note "Branch IDs are for tracing, not logic"
    Branch IDs are great for debugging and understanding execution paths, but your application code should generally avoid relying on their literal string values.

## The recommended learning path

If you are learning Elan for the first time, prefer this progression:

1. Plain `@task` functions to keep business logic pure.
2. `Node(run=..., next="...")` for clear, explicit routing.
3. Passing workflow input directly into the start task before learning explicit `bind_input` or `bind_output`.
4. Plain Pydantic models for structured data before diving into advanced references (`@ref`).
5. Linear workflows before tackling branching forms.

This gives you the smallest stable mental model before adding complexity like branching, structured payloads, or joins.

### Next steps:

- [Core Concepts](core-concepts.md) for the durable model of `Task`, `Node`, `Workflow`, and `WorkflowRun`.
- [Linear Workflows](../guides/linear-workflows.md) for more linear patterns.
