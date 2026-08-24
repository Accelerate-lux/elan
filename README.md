# Elan

Elan is a Python workflow orchestrator for AI agents, data pipelines, and
applications that require complex, multi-stage workflows. A workflow can
branch, run tasks in parallel, join them again, call another workflow, or add
steps while it runs.

Routes, bindings, fan-out, and joins are defined on the workflow, not inside
task functions. The graph stays visible and tasks only deal with their inputs
and outputs.

Tasks are typed, and Elan validates the graph before running it. Runtime
expansion is Experimental.

> Elan is alpha software and its APIs may change. See the
> [status page](https://accelerate-lux.github.io/elan/status/) for current
> feature availability.

## Installation

Elan requires Python 3.11 or later.

```bash
pip install "elan-workflow @ git+https://github.com/Accelerate-lux/elan.git"
```

## Quick start

```python
import asyncio

from elan import Node, Workflow, task


@task
async def clean_name(name: str) -> str:
    return name.strip().title()


@task
async def render_greeting(name: str) -> str:
    return f"Hello, {name}!"


class GreetingWorkflow(Workflow):
    start = Node(run=clean_name, next="greet")
    greet = render_greeting


run = asyncio.run(GreetingWorkflow().run(name=" elan "))
assert run.result == "Hello, Elan!"
```

`clean_name` and `render_greeting` are tasks. `GreetingWorkflow` connects them,
starting with `clean_name` and then running the node named `greet`.

Use a `Workflow` subclass for application code. The inline `Workflow(...)` form
is available for tests, REPL use, and programmatically constructed graphs.

## Workflow patterns

The task functions and other supporting definitions are omitted below.

### Linear flow

`next` connects one node to the next. A terminal task can be assigned directly
when it does not need routing or binding configuration.

`load → transform → store`

```python
from elan import Node, Workflow


class LinearWorkflow(Workflow):
    start = Node(run=load_data, next="transform")
    transform = Node(run=transform_data, next="store")
    store = store_data
```

### Exclusive routing

`route_on` selects one entry from a route mapping. Here `classify_request`
returns a mapping containing a `route` field whose value is either `approve` or
`review`; only the matching task runs.

`classify → approve | review`

```python
from elan import Node, Workflow


class ApprovalWorkflow(Workflow):
    start = Node(
        run=classify_request,
        route_on="route",
        next={"approve": "approve", "review": "review"},
    )
    approve = approve_request
    review = send_for_review
```

### Fan-out and join

A list of targets starts independent branches. `Join` waits for the branches in
its scope and passes their outputs to one task; reducers should not depend on
branch arrival order.

`load → [score, inspect] → result`

```python
from elan import Join, Node, Workflow


class InspectionWorkflow(Workflow):
    start = Node(run=load_record, next=["score", "inspect"])
    score = Node(run=score_record, next="result")
    inspect = Node(run=inspect_record, next="result")
    result = Join(run=summarize_checks)
```

### Workflow composition

A workflow instance can run as a node inside another workflow. The child
workflow keeps its own graph and exposes its result to the parent's next node.

`load → validation workflow → publish`

```python
from elan import Node, Workflow


class PublishWorkflow(Workflow):
    start = Node(run=load_document, next="validate")
    validate = Node(run=validation_workflow, next="publish")
    publish = publish_document
```

### Runtime expansion

Experimental `Expand` passes the previous task's output to a builder. The
builder returns a `Fragment` containing the nodes to run. A workflow must enable
expansion in its policy.

`plan → Expand(Fragment(...)) → result`

```python
from elan import Expand, Node, Workflow, WorkflowPolicy


class PlannedWorkflow(Workflow):
    policy = WorkflowPolicy(allow_runtime_expansion=True)
    start = Node(run=create_plan, next=Expand(build_fragment))
    result = publish_result
```

See [Dynamic execution](https://accelerate-lux.github.io/elan/guides/dynamic-execution/)
for the full `Fragment` example.

## Status

The static workflow features shown above are Available. `Expand` and `Fragment`
are Experimental. Elan does not currently provide persistence, retries and
resume, remote workers, or a control plane.

See [Project status](https://accelerate-lux.github.io/elan/status/) for the full
list of Available, Experimental, Planned, and Direction items.

## Documentation

- [Getting started](https://accelerate-lux.github.io/elan/learn/getting-started/)
- [Recommended patterns](https://accelerate-lux.github.io/elan/learn/recommended-patterns/)
- [Guides](https://accelerate-lux.github.io/elan/guides/dynamic-execution/)
- [API overview](https://accelerate-lux.github.io/elan/reference/api/)
- [Runtime behavior](https://accelerate-lux.github.io/elan/reference/runtime-behavior/)
- [Project status](https://accelerate-lux.github.io/elan/status/)
- [Authoring with coding agents](https://accelerate-lux.github.io/elan/learn/ai-authoring/)

The name, pronounced “ay-lan,” comes from the French *élan*: both momentum and
moose.

![Elan](elan-pic.webp)
