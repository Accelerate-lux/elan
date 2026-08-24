# Getting Started

!!! info "Capability status"
    This guide uses **Available** workflow, task, node, and binding behavior.
    Check the [canonical status ledger](../status.md) before using advanced
    features.

This guide will show you how to define a small Elan workflow, pass input into it, follow how data moves from one task to the next, and read the final result and execution outputs.

By the end of this guide, you will understand:

- How to define reusable tasks using plain Python functions.
- How data automatically flows between tasks using auto-unpacking and type hints.
- How to connect those tasks together into a workflow graph.
- How to pass inputs into the workflow execution.
- How to access the final workflow result and inspect the complete execution log.

## Install the current alpha

The package is not published on PyPI yet. Install the current source:

```bash
pip install "elan-workflow @ git+https://github.com/Accelerate-lux/elan.git"
```

Elan requires Python 3.11 or newer.

## Step 1: define tasks

We define the business logic in plain Python functions `prepare_article`, `publish_article`, and `build_notification` and decorate them with `@task` to make them discoverable by Elan.

```python
import re
from pydantic import BaseModel
from elan import task

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
```

This lets us keep the business logic pure, reusable, and decoupled from the orchestration defined in the workflow.

## Step 2: understand how data moves

By default, Elan passes the output of a task to the next as-is, leaving the responsibility of compatibility to the user. However, because Elan's graph definition syntax does not allow custom mapping logic between tasks (like `**values`), this could force you to pass full objects and pollute your task's business logic with data extraction code.

Elan solves this with a feature we call **auto-unpacking**. When an upstream task is type-hinted to return a structured model (e.g., `-> ArticleDraft`):

```python
ArticleDraft(
    title="Launching Elan 0.1",
    slug="launching-elan-0-1",
    author="Hugo",
)
```

To automatically unpack these fields, Elan relies on type hints on both ends:

- **Upstream:** The task must have a return type hint (e.g., `-> ArticleDraft`) so Elan knows what fields are available.
- **Downstream:** Elan looks at the receiving task's arguments to decide the behavior:
    - **Auto-unpacking:** If it expects specific fields (e.g., `def publish_article(slug: str):`), Elan extracts the matching `slug` field.
    - **As-is passing:** If it expects the full model (e.g., `def publish_article(draft: ArticleDraft):`), Elan passes the whole object without unpacking.

This allows upstream tasks to return meaningful models once, while downstream tasks consume only the fields they need directly.

## Step 3: define the workflow graph

Declare application workflows as `Workflow` subclasses. Class attributes name
the nodes, and `start` is the entrypoint.

```python
from elan import Node, Workflow


class PublishArticleWorkflow(Workflow):
    start = Node(run=prepare_article, next="publish")
    publish = Node(run=publish_article, next="notify")
    notify = build_notification


workflow = PublishArticleWorkflow()
```

`PublishArticleWorkflow()` creates a workflow that can be run more than once.
It starts with `prepare_article`, continues to `publish`, and then runs
`notify`. The terminal `notify` node uses a bare task because it does not need
any routing or binding options.

## Step 4: pass input into the workflow

The workflow is executed with:

```python
import asyncio

run = asyncio.run(
    workflow.run(
        title="  Launching Elan 0.1  ",
        author=" Hugo ",
    )
)
```

Elan binds those named inputs to the start task, so `prepare_article(title: str, author: str)` receives them directly.

## Step 5: inspect the result

After execution, `run.result` contains the final output of our workflow:

```pycon
>>> run.result
'Article ready at /articles/launching-elan-0-1'
```

Because we didn't explicitly define the reserved `result` node, Elan automatically falls back to using the output of the last terminal node (`notify` in this case). This makes simple, linear workflows work out of the box without extra boilerplate.

## Step 6: inspect the outputs log

While `run.result` gives you the final answer, `run.outputs` provides a complete log of everything that happened during execution:

```pycon
>>> run.outputs
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

## Putting it all together

Here is the complete, runnable code for this guide:

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


class PublishArticleWorkflow(Workflow):
    start = Node(run=prepare_article, next="publish")
    publish = Node(run=publish_article, next="notify")
    notify = build_notification


workflow = PublishArticleWorkflow()

if __name__ == "__main__":
    run = asyncio.run(
        workflow.run(
            title="  Launching Elan 0.1  ",
            author=" Hugo ",
        )
    )
    print("Result:", run.result)
```

### Next steps:

- [Core Concepts](core-concepts.md) for the durable model of `Task`, `Node`, `Workflow`, and `WorkflowRun`.
- [Linear Workflows](../guides/linear-workflows.md) for more linear patterns.
