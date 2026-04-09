# Context

This guide shows how Elan workflow context works today.

Context is:

- declared once at the workflow level
- typed with a Pydantic model
- scoped per branch
- readable through `Context.field`
- writable through `Node.context`

## Declare workflow context

```python
from pydantic import BaseModel
from elan import Workflow


class PublishContext(BaseModel):
    locale: str = "en"
    prefix: str = "draft"
    published_url: str | None = None


workflow = Workflow(
    "publish_article",
    context=PublishContext,
    start=...,
)
```

Each workflow run starts with a fresh instance of that model.

## Prepare context before a node runs

Use `Node.context` when a node needs to shape the context visible during its own execution.

```python
from elan import Context, Input, Node


start=Node(
    run=prepare_article,
    context={"prefix": Input.prefix},
    next="publish",
)
```

That update happens before the task executes. If the node or a later node reads `Context.prefix`, it sees the prepared branch-local value.

Supported sources in `Node.context` are:

- literals
- `Input.field`
- `Context.field`
- `Upstream.field` for non-entry nodes

When a non-entry node uses `Node.context`, `Upstream.field` reads from the value emitted by the previous node. If the previous node used `bind_output`, `Node.context` sees that adapted emitted value.

## Branch-local behavior

When a workflow branches, each child branch inherits the parent branch context and then diverges independently.

Sibling branches:

- start from the same inherited context state
- can write different values to the same context key
- do not observe each other's writes

`Join(...)` does not merge branch contexts in this slice. It only reduces result contributions.

## Validation rules

Current validation is strict:

- `Node.context` requires a declared workflow context model
- unknown context fields fail clearly
- values are validated against the context model schema
- bare model field refs like `Payload.key` are not valid sources here; use `Input/Context/Upstream` refs instead

For exact runtime semantics, see [Runtime Behavior](../reference/runtime-behavior.md).
