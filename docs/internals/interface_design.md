# Interface Design

This document captures the intended public interface for Elan.

It is a design note. It describes the interface shape Elan is built around, including features that are not implemented yet.

## Public Vocabulary

Elan uses a small top-level vocabulary:

- `Workflow`: orchestration definition
- `task`: registered executable callable
- `Node`: configured use of a task inside a workflow
- `WorkflowRun`: execution of a workflow, including its exported `result` value when defined
- `Context`: scoped execution state declared by the workflow

The split is intentional:

- a task describes work
- a node describes how that work participates in a workflow
- a workflow describes orchestration
- a run is one concrete execution of that workflow
- context carries scoped execution state

## Canonical Python Shape

The smallest workflow is a single task:

```python
import elan as el
from elan import Workflow


@el.task
def hello():
    return "Hello, world!"


workflow = Workflow(
    "hello_world",
    start=hello,
)
```

That is the baseline shape Elan preserves.

## Workflows

Elan workflows have two reserved graph entry points:

- `start`: the first node to execute
- `result`: the terminal node whose exposed value becomes the workflow export

`result` is a normal node in the graph. It is still configured with `Node(...)`.

In the Python API, `result=` is the reserved keyword node.

In config and API payloads, `result` is the reserved node id.

What makes it special is its role in the workflow contract:

- it is the outward-facing result of the workflow
- its exposed value is stored on `WorkflowRun.result`
- when a workflow is used inside `Node(run=child_workflow)`, that exported value is what the parent receives as the child node output

That keeps sub-workflow composition explicit. A child workflow does not silently expose its last value or its full `WorkflowRun`.

Intended shape:

```python
import elan as el
from elan import Node, Workflow


@el.task
def prepare():
    return 2, 3


@el.task
def add(left: int, right: int):
    return left + right


workflow = Workflow(
    "sum_ab",
    start=Node(run=prepare, next="result"),
    result=Node(run=add),
)
```

`Workflow.run(...)` still returns `WorkflowRun`.

If the workflow defines `result`, the exported value is available on `WorkflowRun.result`.

`result` is terminal. It does not route further through `next`.

For a single-node workflow, `start` may point directly to `result`.

## Workflow Context

Context is declared at the workflow level.

It is a pre-declared model, not an open dictionary.

That gives Elan:

- typed execution state
- validated reads and writes
- one stable schema across all branch scopes

Intended shape:

```python
import elan as el
from pydantic import BaseModel
from elan import Workflow


@el.ref
class RunContext(BaseModel):
    user_id: int | None = None
    locale: str = "en"
    surname: str | None = None


workflow = Workflow(
    "example",
    context=RunContext,
    start=...,
)
```

Each execution scope carries a value of that model.

When the graph branches, context branches with it. Sibling branches may write the same keys with different values without seeing each other. Join and merge behavior decides what is promoted outside the branch scope.

All context updates follow the same base rule:

- they merge field by field into the current branch scope
- unknown fields are invalid by schema

## Refs

Elan uses registered ref classes for typed field references in the workflow DSL.

`@el.ref` marks a class as referenceable and registers it under a stable id.

That ref concept is used for:

- workflow context model ids
- structured return-model field references in `When(...)`
- possible future structured return-model field references in deferred post-execution hooks

Intended shape:

```python
import elan as el
from elan import Node, Workflow
from pydantic import BaseModel


@el.ref
class RoutePayload(BaseModel):
    should_email: bool
    key: str
```

In config and API payloads, the class name is the registry id:

```yaml
context: RunContext
```

and field references serialize as:

```yaml
$RoutePayload.should_email
```

## Nodes

Use a bare task when no extra configuration is needed.

Use a `Node` when the workflow needs to define:

- the next step
- input adaptation
- output adaptation
- context preparation
- routing

The intended `Node` surface is:

- `run`
- `input`
- `context`
- `output`
- `next`
- `route_on`

`run` may execute either a task or another workflow.

When `run` executes a child workflow, the node receives the child workflow's exported `result` value, not the full `WorkflowRun`.

Minimal linear workflow:

```python
import elan as el


@el.task
def normalize_name(name: str):
    return name.strip().title()


@el.task
def greet(name: str):
    return f"Hello, {name}!"


workflow = Workflow(
    "greet_world",
    start=Node(
        run=normalize_name,
        bind_output="name",
        next="greet",
    ),
    greet=greet,
)
```

## Node Execution Flow

For one node execution, Elan applies these phases in order:

1. `input`: prepare task arguments when the workflow needs to adapt what the task receives
2. `context`: prepare scoped context when the workflow needs to shape the context visible during task execution
3. `run`: execute the task and produce its result
4. `output`: adapt the result when the workflow needs to reshape what the node emits
5. `next`: route execution when the workflow continues beyond the current node

These phases are optional. A node only declares the parts it needs.

That keeps the simple case small:

```python
Node(run=hello)
```

and lets complexity appear only when the workflow actually needs it.

This ordering also makes the phase boundaries explicit:

- `input` and `context` are pre-execution
- `output` is post-execution
- `next` routes the execution that remains after those phases have completed

## Type System

Elan's type system is part of a broader workflow validation system.

It validates:

- graph integrity
- workflow contracts
- type compatibility
- runtime-materialized graph structure

The type system is designed around workflow surfaces Elan can reason about:

- task signatures
- task return annotations
- yielded item types
- context schema
- `input`
- `output`
- `context`
- routing
- composition boundaries
- `Join(...)`

The validation model has three layers:

1. static graph validation
2. static type validation
3. semi-static runtime validation

Static graph validation catches structural problems such as:

- missing `start` or `result`
- unknown routing targets
- stray unreachable nodes
- invalid `Join` placement
- invalid routing shapes

Static type validation checks known workflow contracts such as:

- input compatibility
- output adaptation
- context reads and writes
- routing fields
- child workflow result boundaries
- join reducers

Semi-static runtime validation covers graph structure and packets that are only knowable at execution time, especially for `yield`, dynamic expansion, and runtime join contributions.

This validation system remains strong when type information is available and degrades gracefully when tasks are only partially typed.

The full requirements are captured in [type_system_requirements.md](/C:/Users/Hugod/Workspace/elan/docs/internals/type_system_requirements.md).

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

`Node.bind_output` is the explicit output adapter.

It is used when a node must:

- rename a returned value
- expose only part of a multi-value return
- discard values that should not move forward

Examples:

```python
bind_output="name"
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
bind_output=["name", "style"]
bind_output=[..., "style"]
```

In Python, `...` discards a returned position. In config, the equivalent is `null`.

## Input Mapping

`Node.bind_input` is the explicit input adapter.

It is used when a node must consume:

- selected values from the immediate upstream node
- values from the workflow input
- values from the workflow context
- literals

The Python API uses reference objects:

```python
import elan as el
from elan import Context, Input, Node, Upstream, Workflow


@el.task
def build_profile(name: str, surname: str, locale: str, formal: bool):
    return f"{name} {surname} ({locale}) formal={formal}"


workflow = Workflow(
    "profile",
    start=Node(
        run=build_profile,
        bind_input={
            "name": Upstream.name,
            "surname": Input.surname,
            "locale": Context.locale,
            "formal": True,
        },
    ),
)
```

The config form uses the serialized reference syntax:

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

Arbitrary references to other named nodes are not part of `Node.bind_input`.

That keeps `Node.bind_input` focused on adaptation. Multi-node mixing and join semantics belong to explicit synchronization features, not to ordinary input mapping.

## Context Preparation

`Node.context` prepares the context before the node executes.

It is part of the pre-execution phase, alongside `Node.bind_input`.

That makes one thing explicit: it defines the context view the task sees when it runs.

Intended shape:

```python
import elan as el
from pydantic import BaseModel
from elan import Context, Input, Node, Upstream, Workflow


@el.ref
class RunContext(BaseModel):
    user_id: int | None = None
    locale: str = "en"
    surname: str | None = None


@el.task
def build_profile(name: str, surname: str, locale: str, formal: bool):
    return f"{name} {surname} ({locale}) formal={formal}"


workflow = Workflow(
    "profile",
    context=RunContext,
    start=Node(
        run=build_profile,
        bind_input={
            "name": Upstream.name,
            "surname": Input.surname,
            "locale": Context.locale,
            "formal": True,
        },
        context={
            "surname": Input.surname,
        },
    ),
)
```

The `context` field on a node declares the context values that are prepared before task execution.

The config form uses the same reference model:

```yaml
context: RunContext

nodes:
  build_profile:
    run: build_profile
    input:
      name: $upstream.name
      surname: $input.surname
      locale: $context.locale
      formal: true
    context:
      surname: $input.surname
```

Ordinary nodes read freely from context through `Node.bind_input`. `Node.context` prepares scoped context before the task runs.

## Deferred Post-Execution Hooks

Post-execution node hooks such as `after` are currently deferred.

If Elan adds them later, they should remain declarative, run after successful execution, and stay separate from callback-style runtime hooks.

One possible future shape:

```python
import elan as el
from pydantic import BaseModel
from elan import Context, Node, When, Workflow


@el.ref
class RunContext(BaseModel):
    user_id: int | None = None
    locale: str = "en"
    key: str | None = None


@el.ref
class RoutePayload(BaseModel):
    should_email: bool
    key: str


@el.task
def classify(name: str) -> RoutePayload:
    return RoutePayload(
        should_email=True,
        key="abc123",
    )

workflow = Workflow(
    "conditional_routes",
    context=RunContext,
    start=Node(
        run=classify,
        after={
            "context": {
                Context.key: RoutePayload.key,
            },
        },
        next=[
            When(RoutePayload.should_email, "send_email"),
        ],
    ),
    send_email=send_email,
)
```

If this surface is added later, it should stay phase-specific:

- it runs only after successful execution
- it sees the adapted output
- `after.context` may update multiple context keys

The important distinction is that any future `after` surface should stay declarative. Callback-style hooks remain deferred.

## Workflow Composition

Sub-workflows compose through ordinary nodes.

That is the public composition model:

- a node is the execution site
- `run` is the executable
- the executable may be a task or a workflow

Intended shape:

```python
import elan as el
from elan import Node, Workflow


@el.task
def prepare():
    return 2, 3


@el.task
def add(left: int, right: int):
    return left + right


@el.task
def identity(value: int):
    return value


sum_ab = Workflow(
    "sum_ab",
    start=Node(run=prepare, next="result"),
    result=Node(run=add),
)


workflow = Workflow(
    "use_child",
    start=Node(run=sum_ab, next="result"),
    result=Node(run=identity),
)
```

This makes composition graph-native.

The child workflow remains reusable because its outward contract is declared once, through `result`.

The parent does not bind against the child's full execution object. It binds against the child's exported value.

## Join

`Join` is the first-pass synchronization and reduction primitive.

It is a public graph element.

In the first pass, `Join` is only allowed as the reserved `result` node.

That keeps the model narrow:

- composition happens through sub-workflows
- branching happens inside those workflows
- joins close the workflow scope and produce the exported result

Intended shape:

```python
import elan as el
from elan import Join, Node, Workflow


@el.task
def pair_inputs(a: int, b: int, c: int, d: int):
    yield a, b
    yield c, d


@el.task
def multiply_pair(left: int, right: int) -> int:
    return left * right


@el.task
def sum_values(values: list[int]) -> int:
    return sum(values)


workflow = Workflow(
    "sum_products",
    start=Node(run=pair_inputs, next="multiply"),
    multiply=Node(run=multiply_pair, next="result"),
    result=Join(run=sum_values),
)
```

This computes:

```text
(a * b) + (c * d)
```

`Join` follows these execution rules:

- it waits for the current workflow scope to complete
- it collects the packets that were explicitly routed to `result`
- branches that do not route to `result` are still awaited, but do not contribute values
- if `run` is provided, the collected values are passed to that reducer
- the reduced value becomes `WorkflowRun.result`

That makes `Join` the explicit promotion point from branch-local work into the workflow's exported result.

The simplest form is:

```python
result=Join()
```

In that form, the workflow result is the collected list itself.

The reducer form is:

```python
result=Join(run=reduce_values)
```

In that form, the reducer receives the collected contributions as one value.

The first-pass contract is intentionally strict:

- `Join` is terminal
- `Join` waits on workflow completion, not on selected internal nodes
- finer-grained synchronization uses smaller sub-workflows

This also fits the yield placement rules:

- `yield -> sub_workflow(...)` creates several independent child workflow executions
- `sub_workflow(yield -> ...)` creates coupled internal branches that may converge through `Join`

### Future Mid-Graph Join Direction

Mid-graph joins remain deferred.

If Elan later allows `Join` outside `result`, it reuses the same `Join(...)` surface instead of introducing a second join syntax.

The design direction is:

- a mid-graph join is tied to one upstream yield-producing task execution
- that yield-producing execution defines the branch family
- the producer finishing emission closes that family
- the join waits for the branches between that producer and the join to settle

That direction keeps dynamic branch cardinality compatible with joins without forcing a statically paired split-and-join model.

Nested or repeated fan-out before a join still needs a more complete family-resolution rule.

That work stays out of the first implementation.

## Dynamic Execution

Dynamic execution extends the graph at runtime.

The graph evolution model is append-only.

That means Elan may materialize new continuation steps at runtime, but it does not rewrite already-materialized nodes or reroute already-scheduled execution.

Expansion is also controlled at the workflow level.

A workflow may explicitly allow or forbid dynamic expansion inside its own scope.

Intended shape:

```python
from elan import BoundaryPolicy, Policy, Workflow


Workflow(
    "static_child",
    policy=Policy(
        boundaries=BoundaryPolicy(
            allow_expansion=False,
        ),
    ),
    start=...,
    result=...,
)
```

This matters for both execution and validation:

- it gives users a clean way to disable expansion in sub-workflows
- it lets Elan reject `Expand(...)` and callable `next` statically when expansion is not allowed in that workflow

Dynamic expansion belongs to `next`.

Static continuation still looks like:

```python
next="revalidate"
```

The common dynamic shorthand is a bare callable:

```python
next=build_dependencies
```

That is equivalent to:

```python
next=Expand(build_dependencies)
```

The explicit `Expand(...)` form is used when the dynamic continuation needs extra metadata, especially a `then` continuation anchor.

Dynamic continuation uses `Expand(...)`:

```python
import elan as el
from elan import Expand, Node, Workflow


@el.task
def validate():
    ...


def build_dependencies(...) -> Workflow | dict[str, Node] | Node | None:
    ...


workflow = Workflow(
    "dynamic_example",
    start=Node(
        run=validate,
        next=Expand(build_dependencies, then="revalidate"),
    ),
    revalidate=Node(run=validate),
)
```

`Expand(...)` keeps `next` clean while making the dynamic case explicit.

The builder may return:

- `None`
- `Node`
- a workflow-shaped node fragment
- `Workflow`

`then` is the static continuation anchor.

That solves the insertion case cleanly:

- the expansion may append nodes before an already-declared continuation
- the continuation node is not stray, because it is referenced statically through `then`
- the runtime appends the materialized continuation fragment and wires its terminal continuation to `then`

This allows both:

- whole workflow generation
- direct expansion of the current local workflow scope without forcing a sub-workflow boundary every time

Dynamic graph validation follows the same incremental rule as the execution model:

- Elan validates the graph as it is currently materialized
- a returned fragment may route directly to existing static nodes
- if the returned structure does not reference an existing continuation itself, `then` provides the continuation anchor
- if the returned structure itself contains `Expand(...)`, that nested dynamic continuation is validated later, when it materializes

So the validator does not try to prove the entire future graph upfront.

It validates the known current graph and defers only the parts that are still genuinely dynamic.

The structural guardrails for dynamic execution are:

- append-only materialization
- no rewriting of already materialized nodes or routes
- valid current graph after each expansion
- `then` must exist when it is used
- returned structures are validated as currently materialized
- `Join` remains restricted to `result`
- dynamic fragments may reference existing static nodes, but may not mutate them

The current design defines the expansion mechanism itself.

Validation rules, guardrails, recursion limits, and other runtime boundaries remain in later work.

## Cycles

Static cycles are part of the graph language.

They model declared recurrence.

Dynamic expansion and static cycles solve different problems:

- static cycles express recurrence in the declared graph
- dynamic expansion expresses graph growth at runtime

Cycle use is controlled through workflow policy.

Intended shape:

```python
from elan import BoundaryPolicy, Policy, Workflow


Workflow(
    "agent_loop",
    start=...,
    result=...,
    policy=Policy(
        boundaries=BoundaryPolicy(
            allow_cycles=True,
        ),
    ),
)
```

Cycle rules:

- cycles are invalid unless the workflow policy allows them
- when cycles are allowed, they remain subject to graph validation and type validation
- cycle safety is enforced through runtime policy rather than by forbidding recurrence

The runtime policy surface for cycle safety includes:

- cycle opt-in
- point-in-time graph budgets
- cumulative graph budgets
- time budgets

Policies are objects so they can be reused across workflow boundaries.

That allows one workflow to carry a top-level policy while a sub-workflow reuses the same policy object or applies a narrower one.

Static cycles and dynamic expansion use the same guardrail system, but they remain separate graph features.

## Structured Payloads

Elan supports native structured payloads through Pydantic models.

Pydantic models are the named payload mechanism. Raw dictionaries are not.

That gives Elan one path for validated field binding without making every mapping value behave like workflow syntax.

Example:

```python
import elan as el
from pydantic import BaseModel
from elan import Node, Workflow


@el.ref
class UserPayload(BaseModel):
    name: str
    age: int


@el.task
def build_user() -> UserPayload:
    return UserPayload(name="Ada", age=32)


@el.task
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

Branching is any routing form that creates child execution paths.

All branching forms follow the same scope rule:

- each resulting branch gets its own child execution scope
- that child scope inherits the parent scoped context
- sibling branches do not see each other's scoped context updates

The main branching forms are:

- exclusive branching
- conditional multi-routing
- fan-out
- yield-based fan-out

### Exclusive Branching

Exclusive branching uses the `dict` form of `next`.

The workflow declares which output field selects the route through `route_on`.

For simple named outputs, `route_on` may stay a string:

```python
route_on="style"
```

For structured return models, the same intent may also be expressed through registered ref fields:

```python
route_on=RoutePayload.style
```

Intended shape:

```python
import elan as el
from elan import Node, Workflow


@el.task
def choose_greeting(name: str, formal: bool):
    cleaned_name = name.strip().title()
    style = "formal" if formal else "casual"
    return cleaned_name, style


@el.task
def greet_formal(name: str):
    return f"Hello, {name}."


@el.task
def greet_casual(name: str):
    return f"Hey {name}!"


workflow = Workflow(
    "branching_greet",
    start=Node(
        run=choose_greeting,
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

### Conditional Multi-Routing

Conditional multi-routing uses a list of `When(...)` objects in `next`.

This is different from exclusive branching:

- exclusive branching selects one route from a mapping
- conditional multi-routing may activate zero, one, or many downstream nodes

Each `When(...)` is evaluated independently.

Order does not matter.

Zero matches is valid.

Duplicate destinations are allowed.

`When(condition, [...])` is also valid and behaves like conditional fan-out to several destinations.

Intended shape:

```python
import elan as el
from pydantic import BaseModel
from elan import Node, When, Workflow


@el.ref
class RoutePayload(BaseModel):
    should_email: bool
    should_notify: bool
    should_ticket: bool


@el.task
def classify(name: str) -> RoutePayload:
    return RoutePayload(
        should_email=True,
        should_notify=False,
        should_ticket=True,
    )


workflow = Workflow(
    "conditional_routes",
    start=Node(
        run=classify,
        next=[
            When(RoutePayload.should_email, "send_email"),
            When(RoutePayload.should_notify, "notify_slack"),
            When(RoutePayload.should_ticket, "open_ticket"),
        ],
    ),
    send_email=send_email,
    notify_slack=notify_slack,
    open_ticket=open_ticket,
)
```

The config form serializes the same idea explicitly:

```yaml
next:
  - when: $RoutePayload.should_email
    to: send_email
  - when: $RoutePayload.should_notify
    to: notify_slack
  - when: $RoutePayload.should_ticket
    to: open_ticket
  - when: $RoutePayload.should_email
    to:
      - send_email
      - open_ticket
```

### Fan-Out

Fan-out uses the `list` form of `next`.

The current node output is copied to each downstream node.

Intended shape:

```python
import elan as el
from elan import Node, Workflow


@el.task
def prepare_profile(name: str):
    return name.strip().title()


@el.task
def build_greeting(name: str):
    return f"Hello, {name}!"


@el.task
def build_badge(name: str):
    return f"badge:{name.lower()}"


workflow = Workflow(
    "fan_out_profile",
    start=Node(
        run=prepare_profile,
        bind_output="name",
        next=["build_greeting", "build_badge"],
    ),
    build_greeting=build_greeting,
    build_badge=build_badge,
)
```

### Yield-Based Fan-Out

Yield-based fan-out follows the same routing rules.

Each yielded item is treated like one node output packet and routed independently.

Intended shape:

```python
import elan as el
from elan import Node, Workflow


@el.task
def split_names(names: list[str]):
    for name in names:
        yield name.strip().title()


@el.task
def greet(name: str):
    return f"Hello, {name}!"


workflow = Workflow(
    "yield_fan_out",
    start=Node(
        run=split_names,
        bind_output="name",
        next="greet",
    ),
    greet=greet,
)
```

## Config Shape

Code, config files, and API payloads share the same workflow model.

Minimal YAML shape:

```yaml
name: greet_world
context: RunContext
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
    next: result
  result:
    run: identity
```

The important points are:

- `run` points to a registered task id
- workflow invocation carries an explicit `input` object
- workflows may declare a context model
- workflows may declare a reserved `result` node
- nodes may declare `input`, `output`, `context`, and `next`

Config references follow the same model as the Python API:

- `$input.foo`
- `$upstream.foo`
- `$context.foo`
- `$context`
- `$RoutePayload.should_email`

Example with both input adaptation and context preparation:

```yaml
name: profile
context: RunContext
start: build_profile
nodes:
  build_profile:
    run: build_profile
    input:
      name: $upstream.name
      surname: $input.surname
      locale: $context.locale
      formal: true
    context:
      surname: $input.surname
```

If Elan adds post-execution hooks later, a possible config shape could be:

```yaml
after:
  context:
    key: $RoutePayload.key
```

## API Shape

The HTTP API accepts the same workflow spec directly.

The API exposes the same workflow model instead of introducing a different orchestration format for HTTP clients.

Suggested endpoints:

- `POST /v1/workflows/runs`
- `GET /v1/workflows/runs/{run_id}`

Minimal create-run request:

```json
{
  "workflow": {
    "name": "hello_world",
    "context": "RunContext",
    "start": "result",
    "nodes": {
      "result": {
        "run": "hello"
      }
    }
  },
  "input": {}
}
```

Example create-run request with input adaptation and context preparation:

```json
{
  "workflow": {
    "name": "profile",
    "context": "RunContext",
    "start": "build_profile",
    "nodes": {
      "build_profile": {
        "run": "build_profile",
        "input": {
          "name": "$upstream.name",
          "surname": "$input.surname",
          "locale": "$context.locale",
          "formal": true
        },
        "context": {
          "surname": "$input.surname"
        },
        "next": "some_node"
      }
    }
  },
  "input": {
    "surname": "Lovelace"
  }
}
```

Create-run response:

```json
{
  "run_id": "run_123",
  "status": "accepted"
}
```

Run response:

```json
{
  "run_id": "run_123",
  "workflow": "hello_world",
  "status": "succeeded",
  "result": "Hello, world!"
}
```

The final run response shape still needs to be updated once the execution and result model is fully locked down.

## Later Topics

These topics are part of the broader interface design and remain for later work:

- State
  - context write authorization
  - merge and promotion rules
- Validation system rollout
  - implementation strategy for static graph validation
  - implementation strategy for static type validation
  - implementation strategy for semi-static runtime validation
- Error handling
  - error categories and definitions
  - handling behavior for each error type and scope
- Agent features
  - agent state and message history
  - tool-call state and tool authorization
  - pause, resume, interrupt, and human-in-the-loop control
  - persistent vs ephemeral memory
  - multi-agent delegation and coordination
  - streaming outputs and agent-specific result shapes
  - observability and trace policy
  - the boundary between workflow context and agent-local state
- Model surface
  - `After.callback` as an advanced escape hatch
  - whether `after` should later become a dedicated object instead of a plain field
  - the boundary of `after`: whether it should stay limited to context updates or grow to support other post-execution operations
  - explicit edge model
  - workflow run and execution graph shape
  - config and API parity
