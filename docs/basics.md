# Basics

This document explains the basic concepts and usage of Elan.

Elan is built around a small workflow model:

- `task` defines executable logic
- `Workflow` defines orchestration
- `Node` adds workflow behavior around a task when needed
- `WorkflowRun` is the object returned by execution

The easiest way to understand Elan is to start with one task, then add one more task, then look at how data moves between them.

## Tasks

A `task` is a Python callable decorated with `@task`.

```python
from elan import task

@task
async def hello():
    return "Hello, world!"
```

The decorator marks the function as something Elan is allowed to execute. Without it, the runtime refuses to run the callable.

Tasks may be:

- synchronous functions
- asynchronous functions

A task only describes work. It does not describe when it runs, what comes before it, or what comes after it. That is the job of the workflow.

## Workflows

A `Workflow` defines how tasks are orchestrated.

A workflow is a graph of nodes with one node designated as the start node. In the simplest case, a node is just a task. 

The smallest workflow is a single task used as the start node:

```python
from elan import Workflow, task

@task
async def hello():
    return "Hello, world!"

workflow = Workflow("hello_world", start=hello)
run = await workflow.run()
```

In the single-task case, the workflow does one thing: execute the start node and stop.

## Runs

Calling `workflow.run()` creates a workflow run.

A run is the concrete execution of a workflow definition with a specific set of inputs. The workflow tells Elan what should happen; the run is the record of what actually happened for one execution.

This distinction matters because a workflow is reusable, while runs are not. You may define one workflow and execute it many times with different inputs, timings, and outcomes.

`workflow.run()` returns a `WorkflowRun` object.

`WorkflowRun` is meant to represent execution, not just output. Even in the simple form it has today, it already establishes the idea that running a workflow gives you a run object rather than a raw return value.

Right now, `WorkflowRun` stores:

- `result`: a mapping of task name to the list of outputs produced during the run

So the one-task workflow above produces:

```python
{"hello": ["Hello, world!"]}
```

Over time, a run is expected to become the place where execution data lives: task results, graph state, context, logs, and other run-level information.

## Nodes

A `Node` is the configured form of a task inside a workflow. It s used when a task needs to carry workflow-specific behavior such as sequencing, routing or output mapping. 

You can use a bare task when no extra configuration is needed.

The runtime uses these fields:

- `run`
- `next`
- `output`

Conceptually:

- `run` chooses the task to execute
- `next` chooses the next named node
- `output` reshapes the task result before passing it forward

## Linear Flow

Elan supports linear chaining through `next="..."`.

A two-task workflow is defined by:

- choosing a start node
- naming the downstream task in `next`
- registering that downstream task on the workflow

```python
from elan import Node, Workflow, task

@task
def prepare():
    return "world"

@task
async def greet(name):
    return f"Hello, {name}!"

workflow = Workflow(
    "greet_world",
    start=Node(run=prepare, output="name", next="greet"),
    greet=greet,
)

run = await workflow.run()
```

This produces:

```python
{
    "prepare": ["world"],
    "greet": ["Hello, world!"],
}
```

Two things happen here:

- `prepare` is wrapped in a `Node` so the workflow can declare what comes next
- the output of `prepare` is mapped before `greet` receives it

## Output Mapping

A node may map its task output before passing it to the next node.

For a single mapped value:

```python
output="name"
```

If `prepare()` returns:

```python
"world"
```

then Elan turns that into:

```python
{"name": "world"}
```

That mapped value becomes the input for the next task.

Multi-value mappings are also supported:

```python
output=["name", "style"]
output=[..., "style"]
```

The second form ignores positions you do not want to pass forward.

## Input Binding

Elan binds task inputs automatically.

There are two binding modes.

### Dict binding

If the current input is a dictionary, task parameters are matched by key.

So this works naturally:

```python
{"name": "world"}
```

for:

```python
async def greet(name):
    ...
```

### Single-value binding

If the current input is a single value and the task has exactly one parameter, that value is bound to that parameter automatically.

For example:

```python
@task
def double(x):
    return x * 2
```

can receive `21`, and Elan binds it as:

```python
{"x": 21}
```

This keeps the common case simple while still letting nodes reshape outputs explicitly when needed.

## Sync and Async Tasks

`Workflow.run()` is asynchronous.

Execution works like this:

- async tasks are awaited directly
- sync tasks are executed with `asyncio.to_thread(...)`

That means synchronous tasks do not block the event loop even though the workflow runtime itself is async.

## Unsupported Features

These features are not supported by the runtime:

- branching
- fan-out
- `next` as `list`
- `next` as `dict`
- explicit input mapping through `Node.input`
- routing through `route_on`
- sub-workflows
- barriers and joins
