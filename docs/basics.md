# Basics

This guide introduces the core concepts and usage of Elan.

Elan is a workflow orchestrator designed around a graph-based execution model. You build workflows by defining discrete tasks as nodes and establishing the execution paths between them. 

To make orchestration intuitive, Elan relies on a few core design principles:

* **Coupled Transitions:** Rather than defining nodes and edges in separate configurations, Elan uses transitory nodes. A node's definition inherently dictates its routing logic to the next step, meaning workflows naturally form a **directed graph**. This keeps the flow of execution localized and declarative.
* **Direct Data Passing:** While Elan supports a distributed shared state for complex requirements, the canonical approach is for nodes to pass data directly to one another. This keeps data dependencies explicit, predictable, and easy to test.
* **Sensible Defaults:** The API is designed to get out of your way. Elan provides default behaviors for standard routing, ensuring that simple workflows require minimal boilerplate to get running.


To build these directed graphs, Elan separates the execution of work from its orchestration using three core concepts:

* **Task:** The fundamental unit of work. A task represents a discrete unit of business logic, kept entirely independent of the orchestration layer.
* **Node:** The routing wrapper for a task. In a graph, a task alone is insufficient because it lacks routing information. A node encapsulates both the task to be executed and the routing logic (the edges) that determines the next step.
* **Workflow:** The orchestrator. It manages the execution state of the nodes and coordinates the flow of data across the graph.

## Defining Tasks

A task is the basic unit of execution in Elan. It is defined as a standard Python function—either synchronous or asynchronous—and registered with the Elan runtime by applying Elan's `@task` decorator. 

```python
from elan import task

@task
async def hello():
    return "Hello, world!"
```

The decorator does not alter the core behavior of your function. A task's only responsibility is to describe the work it performs. It intentionally knows nothing about what runs before it, what runs after it, or how its output is used. That separation ensures tasks remain highly reusable and easy to test in isolation.

The workflow runtime itself is fully asynchronous (`await workflow.run()`). When executing your graph, Elan awaits asynchronous tasks directly, and automatically executes synchronous tasks in a separate thread (`asyncio.to_thread`). This keeps the orchestrator non-blocking without forcing you to write every task asynchronously.

## Task Identity and Registration

When you decorate a function, Elan automatically registers it using a canonical identity derived from its import path (e.g., `my_project.tasks.hello`). 

This is to prevents name collisions. In large projects, you might have multiple tasks named `process_data` in different modules. By using the import path as the canonical key, Elan guarantees that every task is uniquely identifiable without requiring manual namespace management.

If the canonical import path is too long or cumbersome to reference in your workflows, you can define an explicit alias:

```python
@task(alias="bonjour")
async def hello():
    return "Hello, world!"
```

Aliases provide a convenient shorthand for workflow definitions, but the canonical key always remains the stable underlying identity.

## Orchestrating with Workflows

A `Workflow` acts as the blueprint for your execution graph. It defines the topology of your nodes and coordinates the flow of data between them.

Every workflow requires a designated `start` node, which serves as the entry point for execution. In the simplest scenario, the start node can just be a bare task, making the smallest possible workflow a single-step execution:

```python
from elan import Workflow, task


@task
async def hello():
    return "Hello, world!"


workflow = Workflow("hello_world", start=hello)
run = await workflow.run()
```

When constructing the graph, the workflow needs to reference the tasks it will orchestrate. Elan supports three referencing methods to balance strict and loose coupling depending on your project's architecture:

* **Directly:** Passing the `Task` object itself. This is straightforward for small scripts and single-file projects.
* **By canonical key:** Using the task's import path string. This enables loose coupling and helps prevent circular imports in larger, multi-module codebases.
* **By explicit alias:** Using the custom string alias defined on the task. This keeps workflow definitions concise and highly readable.

## Executing Runs

While a `Workflow` acts as a reusable blueprint, a **Run** is a single, concrete execution of that blueprint with a specific set of inputs.

Calling `await workflow.run()` executes the graph and returns a `WorkflowRun` object.

`WorkflowRun.outputs` is the execution report: a dictionary grouped first by branch id, then by executed task name. For the single-task workflow above, the run produces:

```python
{
    "branch-1": {
        "hello": ["Hello, world!"],
    }
}
```

When the workflow defines the reserved `result` node, its exported value is available on `WorkflowRun.result`.

If no reserved `result` node is defined, `WorkflowRun.result` falls back to the last terminal output of the run.

## Configuring Nodes

While a task defines *what* work happens, a `Node` defines *where* that work sits within the execution graph. It acts as a wrapper that attaches routing and data-shaping instructions to an underlying task.

If a task is the final step in a workflow—or the only step—you can pass the bare task directly to the workflow for convenience. However, the moment your workflow needs to dictate what happens after the task completes, you must wrap it in a `Node`.

A `Node` uses three primary fields to establish its context within the graph:

* **`run`**: Specifies the task to execute.
* **`next`**: Defines the directed edge to the next node in the workflow.
* **`bind_output`**: Acts as a data adapter, reshaping the task's result before it moves downstream.

By keeping these routing concerns on the `Node` rather than the task itself, Elan ensures your core business logic remains entirely decoupled from the workflow's topology.

## Building a Linear Flow

The most common graph topology is a simple linear chain. In Elan, you build this by defining directed edges using the `next` field on your nodes.

To create a two-task workflow, you need to:
1. Designate a starting node.
2. Tell that start node where to go by setting `next` to the name of the downstream node.
3. Register the downstream node on the workflow.

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

This execution produces:

```python
{
    "branch-1": {
        "prepare": ["world"],
        "greet": ["Hello, world!"],
    }
}
```

on `run.outputs`.

Notice how `prepare` is wrapped in a `Node`. Because it is not the final step, it requires the `next` field to point the graph toward `greet`. The raw string returned by `prepare` is automatically passed as the first positional argument to `greet`.

## Task Resolution By Name

Because tasks are globally registered, a workflow does not need to import the `Task` object directly. It can reference tasks by their canonical key or alias. This is particularly useful for keeping workflow definitions clean and avoiding circular dependencies.

Here is the same linear flow, but using string aliases:

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

It is important to distinguish between *task names* and *node names*. The `run` field resolves tasks from the global registry. The `next` field, however, always refers to the local node names defined within the `Workflow` itself (in this case, `"greet_node"`).

## Data Binding

Binding is the mechanism by which the output of one node becomes the input of the next node. 

Elan uses a small set of default binding rules designed to keep common workflows concise, while preserving the natural behavior of ordinary Python values. The overarching philosophy is straightforward:

* **Fixed-shape outputs** (like scalars and tuples) move positionally.
* **Structured payloads** (like Pydantic models) move by named fields.
* **Plain Python containers** (like lists and dicts) remain opaque values and are not automatically unpacked.

Understanding how data flows through your graph comes down to five specific binding cases.

### 1. Workflow Entrypoint Binding

The first binding case happens before the graph even starts executing. When you call `workflow.run(**kwargs)`, Elan binds those named keyword arguments directly to the parameters of the `start` node's task.

```python
from elan import Workflow, task


@task
async def greet(name: str):
    return f"Hello, {name}!"


workflow = Workflow("hello_world", start=greet)
run = await workflow.run(name="world")
```

By following standard Python keyword invocation, the entrypoint stays familiar and explicit.

### 2. Positional Argument Passing

When a task returns a fixed-shape output, Elan binds that data to the downstream task positionally. There are exactly two cases where this happens: scalar values and tuples.

**Scalar Output:** If a node returns a single value (like a string, integer, or custom object) and the next task expects exactly one parameter, Elan passes that value through directly. No extra configuration is needed.

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
```

**Tuple Output:** If a node returns a tuple, Elan unpacks it and binds the elements positionally to the next task's parameters. Because this relies on strict ordering, the length of the tuple must exactly match the number of parameters expected downstream.

```python
from elan import Node, Workflow, task


@task
def prepare():
    return "hello", "world"


@task
async def greet(prefix: str, name: str):
    return f"{prefix.title()}, {name}!"


workflow = Workflow(
    "greet_world",
    start=Node(run=prepare, next="greet"),
    greet=greet,
)
```

Here, `"hello"` binds to `prefix` and `"world"` binds to `name`.

Tuple binding is reserved for fixed-shape data. That keeps positional flow simple and predictable.

### 3. Opaque Container Passing

Plain Python collections, like lists and raw dictionaries, are treated as opaque values. Elan does not attempt to automatically unpack them or guess their internal structure.

If a task returns a list or a dict, that entire collection is passed as a single positional argument to the next task.

```python
from elan import Node, Workflow, task


@task
def prepare():
    return {"name": "world"}


@task
async def greet(payload: dict[str, str]):
    return f"Hello, {payload['name']}!"


workflow = Workflow(
    "greet_world",
    start=Node(run=prepare, next="greet"),
    greet=greet,
)
```

In this example, the dictionary is passed as one value to the `payload` parameter. Raw dictionaries are ordinary Python values and are **not** automatically unpacked into keyword arguments.

### 4. Structured Payload Auto-Unpacking

While raw dictionaries are opaque, Elan natively supports structured payloads through Pydantic models. 

When a task returns a Pydantic model, Elan inspects the signature of the downstream task to determine how to bind the data. It uses one of two behaviors:

**Auto-Unpack Fields:** If the downstream task expects specific fields that match the model's attributes, Elan automatically unpacks the model and binds those fields by name.

```python
from pydantic import BaseModel
from elan import Node, Workflow, task


class UserPayload(BaseModel):
    name: str
    age: int


@task
def prepare() -> UserPayload:
    return UserPayload(name="world", age=32)


@task
async def greet(name: str):
    return f"Hello, {name}!"


workflow = Workflow(
    "greet_world",
    start=Node(run=prepare, next="greet"),
    greet=greet,
)
```
In this example, `greet` automatically receives `name="world"`.

**Pass Through The Model:** If the downstream task explicitly expects the Pydantic model type itself, Elan bypasses unpacking and passes the model instance through as a single positional argument.

```python
@task
async def greet(user: UserPayload):
    return f"Hello, {user.name}!"
```

By using type hints on the receiving task, you have full control over which of these two behaviors Elan applies.

### 5. Explicit Output Adaptation

While automatic binding handles the most natural cases, sometimes the output of one task doesn't perfectly match the input signature of the next. Instead of writing boilerplate "adapter tasks," Elan lets you reshape the data directly on the `Node` using the `bind_output` parameter.

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
    start=Node(run=prepare, bind_output="name", next="greet"),
    greet=greet,
)
```

By setting `bind_output="name"`, you explicitly wrap the raw string returned by `prepare` into a named payload (`{"name": "world"}`). The downstream `greet` task then binds to it by parameter name.

This mechanism also supports multi-value mappings for tuples:

```python
# Maps a 2-tuple to two named parameters
bind_output=["name", "style"]

# Discards the first value of a 2-tuple, maps the second to "style"
bind_output=[..., "style"]
```

The `bind_output` field acts as a lightweight adapter layer, ensuring your tasks remain decoupled even when their interfaces don't align perfectly.

### 6. Explicit Input Adaptation

`Node.bind_input` lets you prepare the downstream task call explicitly.

The simplest form uses literal values:

```python
from elan import Node, Workflow, task


@task
def prepare():
    return "world"


@task
async def greet(name: str, punctuation: str):
    return f"Hello, {name}{punctuation}"


workflow = Workflow(
    "greet_world",
    start=Node(run=prepare, next="greet"),
    greet=Node(run=greet, bind_input={"punctuation": "!"}),
)
```

Explicit values override automatic binding for the parameters they provide. Remaining parameters still use the normal binding rules when possible.

`Node.bind_input` also supports source references:

```python
from pydantic import BaseModel
from elan import Context, Input, Node, Upstream, Workflow, ref, task


class GreetingContext(BaseModel):
    punctuation: str = "!"


@ref
class GreetingPayload(BaseModel):
    name: str


@task
def prepare() -> GreetingPayload:
    return GreetingPayload(name="world")


@task
async def greet(name: str, title: str, punctuation: str):
    return f"Hello, {title} {name}{punctuation}"


workflow = Workflow(
    "greet_world",
    context=GreetingContext,
    start=Node(run=prepare, next="greet"),
    greet=Node(
        run=greet,
        bind_input={
            "name": Upstream.name,
            "title": Input.title,
            "punctuation": Context.punctuation,
        },
    ),
)
```

`@ref` is only required for field-reference features. Ordinary Pydantic binding still works without it.

## First-Pass Branching

The current runtime supports three branching forms.

Exclusive branching uses `next` as a mapping plus `route_on`:

```python
from elan import Node, Workflow, task


@task
def prepare():
    return "world", "formal"


@task
async def greet_formal(name: str):
    return f"Hello, {name}."


@task
async def greet_casual(name: str):
    return f"Hey {name}!"


workflow = Workflow(
    "branching_greet",
    start=Node(
        run=prepare,
        bind_output=["name", "style"],
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

If the task returns a registered ref model, the selector may also come from a ref field:

```python
from pydantic import BaseModel
from elan import Node, Workflow, ref, task


@ref
class RoutePayload(BaseModel):
    name: str
    style: str


@task
def prepare() -> RoutePayload:
    return RoutePayload(name="world", style="formal")


workflow = Workflow(
    "branching_greet",
    start=Node(
        run=prepare,
        route_on=RoutePayload.style,
        next={
            "formal": "greet_formal",
            "casual": "greet_casual",
        },
    ),
    greet_formal=greet_formal,
    greet_casual=greet_casual,
)
```

Fan-out uses `next` as a list:

```python
workflow = Workflow(
    "fan_out_profile",
    start=Node(
        run=prepare,
        bind_output="name",
        next=["greet", "badge"],
    ),
    greet=greet,
    badge=badge,
)
```

Conditional multi-routing uses `When(...)` entries in `next`:

```python
from pydantic import BaseModel
from elan import Node, When, Workflow, ref, task


@ref
class RoutePayload(BaseModel):
    name: str
    should_email: bool
    should_ticket: bool


@task
def classify() -> RoutePayload:
    return RoutePayload(name="world", should_email=True, should_ticket=True)


@task
async def send_email(name: str):
    return f"email:{name}"


@task
async def open_ticket(name: str):
    return f"ticket:{name}"


@task
async def audit(name: str):
    return f"audit:{name}"


workflow = Workflow(
    "conditional_routes",
    start=Node(
        run=classify,
        next=[
            When(RoutePayload.should_email, "send_email"),
            When(RoutePayload.should_ticket, ["open_ticket", "audit"]),
        ],
    ),
    send_email=send_email,
    open_ticket=open_ticket,
    audit=audit,
)
```

List-based branching is evaluated left to right. Plain node ids and `When(...)` entries may be mixed in the same `next=[...]` list:

```python
workflow = Workflow(
    "conditional_routes",
    start=Node(
        run=classify,
        next=[
            "audit",
            When(RoutePayload.should_email, "send_email"),
        ],
    ),
    audit=audit,
    send_email=send_email,
)
```

For branched workflows, `run.outputs` stays branch-aware:

```python
{
    "branch-1": {
        "prepare": ["world"],
    },
    "branch-2": {
        "greet": ["Hello, world!"],
    },
    "branch-3": {
        "badge": ["badge:world"],
    },
}
```

If a workflow uses branching forms and does not define the reserved `result` node, `run.result` is `None`.

For `When(...)`, each entry is evaluated independently. Zero matches is valid, and duplicate matched destinations are allowed.

## First-Pass Join On `result`

The current runtime also supports a first terminal join form on the reserved `result` node:

```python
from elan import Join, Node, Workflow, task


@task
def prepare():
    return "world"


@task
async def greet(name: str):
    return f"Hello, {name}!"


@task
async def badge(name: str):
    return f"badge:{name}"


@task
def collect(values: list[str]):
    return " | ".join(values)


workflow = Workflow(
    "fan_out_profile",
    start=Node(
        run=prepare,
        bind_output="name",
        next=["greet", "badge"],
    ),
    greet=Node(run=greet, next="result"),
    badge=Node(run=badge, next="result"),
    result=Join(run=collect),
)
```

`Join` is terminal-only in this first pass:

- it is only allowed as the reserved `result` node
- it collects the emitted values routed to `result`
- `Join()` returns the collected list
- `Join(run=reducer)` calls the reducer with that list as one value
- the reduced result appears on `run.result`
- join reduction is not recorded in `run.outputs`

## Still Unsupported

These features are still not supported by the runtime:

- sub-workflows
- mid-graph joins
- general barriers
