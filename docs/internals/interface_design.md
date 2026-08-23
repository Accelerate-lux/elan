# Interface Design

This document records the implemented local Python interface and the intended
direction for surfaces that do not exist yet. It was audited against the
implementation in August 2026.

## Document Status

The Python API sections describe the current implementation unless they
explicitly say otherwise. Post-execution hooks, config/API authoring, and the
production runtime remain design only.

Current implementation status:

- **implemented:** tasks and registration, workflow construction and subclass
  authoring, binding, refs, context preparation, structured payloads, routing,
  fan-out, yield fan-out, composition, workflow-wide joins, activation-scoped
  joins, concurrent scheduling, explicit `Expand`/`Fragment` graph growth, and
  basic workflow policy;
- **partial:** graph/type validation and static-cycle governance;
- **planned:** post-execution hooks, safe executable cycles, expansion budgets,
  config/API parity, remote execution, persistence,
  reliability controls, and observability. Callable `next` and expansion
  lifecycle continuations are deferred beyond the initial expansion contract.

For the concise feature inventory, see
[Status](../explanations/status.md). Exact runtime behavior lives in
[Runtime Behavior](../reference/runtime-behavior.md).

## Public Vocabulary

Elan uses a small top-level vocabulary:

- `Workflow`: orchestration definition
- `Task` / `task`: registered executable callable and decorator
- `Node`: configured use of a task inside a workflow
- `Join`: synchronization and optional reduction in the graph
- `When`: conditional target production inside `next`
- `WorkflowRun`: execution of a workflow, including its exported `result` value when defined
- `WorkflowPolicy`: immutable execution governance for one workflow run
- `Input`, `Upstream`, `Context`, and `Policy`: field-reference namespaces

Workflow context itself is a user-declared Pydantic model. `Context` is the
reference namespace used to read that model; it is not the state container.

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

**Status: implemented except for terminality validation on ordinary reserved
result nodes.**

Every Elan workflow has one required graph entry point and one optional reserved
export node:

- `start`: the first node to execute
- `result`: the terminal reserved node whose raw return becomes the workflow export

`result` may be an ordinary task/node/workflow or a `Join`.

In the Python API, `result=` is the reserved keyword node.

In the planned config and API representations, `result` is the reserved node id.

What makes it special is its role in the workflow contract:

- it is the outward-facing result of the workflow
- its raw return is stored on `WorkflowRun.result`
- when a workflow is used inside `Node(run=child_workflow)`, that exported value is what the parent receives as the child node output

When `result` exists, it keeps sub-workflow composition explicit: the child
exports that value rather than its full `WorkflowRun`.

For compatibility with minimal workflows, an unbranched workflow without a
reserved `result` exports its last terminal output. A workflow that branches and
does not define `result` exports `None`.

Current shape:

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

The accepted contract is that `result` is always terminal, whether declared as
an ordinary node or as a `Join`. Declaring `next` on either form is invalid and
must be rejected when the workflow is constructed. Epilogue work belongs before
`result` or in a future explicit lifecycle primitive; `result` is not an export
checkpoint in the middle of a graph.

The runtime currently enforces this rule for `result=Join(...)` only. An
ordinary reserved result node can still declare and follow `next`; that is an
implementation gap, not the intended contract.

For a single-node workflow, `start` may point directly to `result`.

Workflows may also be authored as subclasses. Public class attributes declare
the graph, annotation-only `Node` and `Join` attributes provide forward
references, and subclasses may override `run(...)` with a typed signature that
delegates to `_run(...)`.

## Workflow Context

**Status: implemented for pre-execution preparation and scoped reducer
mutation. Post-execution hooks and general merge/promotion policies are not
implemented.**

Context is declared at the workflow level.

It is a pre-declared model, not an open dictionary.

That gives Elan:

- typed execution state
- validated reads and writes
- one stable schema across all branch scopes

Current shape:

```python
import elan as el
from pydantic import BaseModel
from elan import Workflow


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

Each execution scope carries a value of that model. `@ref` is not required for
ordinary context declaration or binding.

When the graph branches, context branches with it. Sibling branches may write
the same keys with different values without seeing each other. Sibling contexts
are not merged automatically by joins.

An activation-scoped join preserves its scope-owner branch. Reducer mutations
therefore remain visible to that join's continuation. A child workflow inherits
a context copy and commits its final context to the parent branch before the
parent continuation executes.

All context updates follow the same base rule:

- they merge field by field into the current branch scope
- unknown fields are invalid by schema

Workflow-level `bind_context` prepares the initial context before `start` runs.
It uses the same reference model as node context preparation, but only has access
to workflow input, literals, and context defaults. It may provide required
context fields from workflow input.

Current shape:

```python
from elan import Input, Workflow


workflow = Workflow(
    "example",
    context=RunContext,
    bind_context={
        "user_id": Input.user_id,
        "locale": Input.locale,
    },
    start=...,
)
```

## Refs

**Status: implemented for the local Python runtime. Config serialization and
remote value references are planned.**

Elan uses registered ref classes for typed field references in the workflow DSL.

`@el.ref` marks a class as referenceable and registers it under a stable id.

The implemented ref concept is used for:

- structured return-model field references in `When(...)`
- structured return-model field references in `route_on`
- typed field lookup through `Upstream`

`Input`, `Context`, `Policy`, and `Upstream` are source namespaces and do not
require a registered model. `@ref` is needed when the workflow declaration uses
class-level model fields such as `RoutePayload.should_email`.

Current shape:

```python
import elan as el
from elan import Node, Workflow
from pydantic import BaseModel


@el.ref
class RoutePayload(BaseModel):
    should_email: bool
    key: str
```

The following config/API serialization is planned, not implemented. The class
name is the proposed registry id:

```yaml
context: RunContext
```

and field references serialize as:

```yaml
$RoutePayload.should_email
```

## Nodes

**Status: implemented.**

Use a bare task when no extra configuration is needed.

Use a `Node` when the workflow needs to define:

- the next step
- input adaptation
- output adaptation
- context preparation
- routing

The current `Node` surface is:

- `run`
- `bind_input`
- `context`
- `bind_output`
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

**Status: implemented.**

For one node execution, Elan applies these phases in order:

1. `context`: prepare the branch context for this activation
2. `bind_input`: prepare task arguments, including reads from the prepared context
3. `run`: execute the task and produce its result
4. `bind_output`: adapt the result when the workflow needs to reshape what the node emits
5. `next`: route execution when the workflow continues beyond the current node

These phases are optional. A node only declares the parts it needs.

That keeps the simple case small:

```python
Node(run=hello)
```

and lets complexity appear only when the workflow actually needs it.

This ordering also makes the phase boundaries explicit:

- `context` and `bind_input` are pre-execution
- `bind_output` is post-execution
- `next` routes the execution that remains after those phases have completed

The raw task return is recorded in `WorkflowRun.outputs`; `bind_output` changes
only the packet emitted downstream.

## Type System

**Status: partial.**

The current runtime validates the contracts it encounters, but it does not yet
perform the full static and semi-static validation system described in
[Type System Requirements](type_system_requirements.md).

Implemented validation includes:

- task registration and task/alias resolution;
- workflow context, binding-target, join-placement, join-scope, and policy
  declaration checks;
- unknown routing targets and invalid routing packets when a route executes;
- static-cycle rejection unless `WorkflowPolicy.allow_cycles` is enabled;
- Pydantic-backed validation of bound task arguments and context updates;
- structured payload, ref-field, and child context/policy compatibility checks.

Not implemented yet:

- whole-graph static type compatibility across edges;
- unreachable/stray-node analysis;
- static validation of every possible route packet;
- runtime-materialized graph validation for expansion;
- observed-type metadata and a unified validation report.

Validation currently happens at the narrowest available boundary: declaration
time where possible, run start for cycle policy, and activation/routing time for
value-dependent checks.

## Binding and Adaptation

**Status: implemented.**

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

In Python, `...` discards a returned position. The proposed config equivalent is
`null`; config authoring is not implemented.

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
            "name": Input.name,
            "surname": Input.surname,
            "locale": Context.locale,
            "formal": True,
        },
    ),
)
```

The planned config form uses the serialized reference syntax:

```yaml
input:
  name: $input.name
  surname: $input.surname
  locale: $context.locale
  formal: true
```

This keeps the Python API object-based while keeping the config form compact.

The supported sources are:

- `Upstream`
- `Input`
- `Context`
- `Policy`
- literals

Arbitrary references to other named nodes are not part of `Node.bind_input`.

That keeps `Node.bind_input` focused on adaptation. Multi-node mixing and join semantics belong to explicit synchronization features, not to ordinary input mapping.

## Context Preparation

`Node.context` prepares the context before the node executes.

It is part of the pre-execution phase, alongside `Node.bind_input`.

That makes one thing explicit: it defines the context view the task sees when it runs.

Current shape:

```python
import elan as el
from pydantic import BaseModel
from elan import Context, Input, Node, Upstream, Workflow


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
            "name": Input.name,
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

The planned config form uses the same reference model:

```yaml
context: RunContext

nodes:
  build_profile:
    run: build_profile
    input:
      name: $input.name
      surname: $input.surname
      locale: $context.locale
      formal: true
    context:
      surname: $input.surname
```

Ordinary nodes read freely from context through `Node.bind_input`. `Node.context` prepares scoped context before the task runs.

## Deferred Post-Execution Hooks

**Status: deferred; no `after` field exists in the public API.**

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

**Status: implemented.**

Sub-workflows compose through ordinary nodes.

That is the public composition model:

- a node is the execution site
- `run` is the executable
- the executable may be a task or a workflow

Current shape:

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

The parent records that exported value under the child workflow's name; child
internal outputs are not merged into the parent output log. Parent
`Node.bind_input` may explicitly construct the child's workflow input. Child
workflows inherit compatible context and policy, and may only narrow an inherited
policy.

## Join

**Status: implemented for workflow-wide terminal joins and activation-scoped
mid-graph joins.**

`Join` is the synchronization and optional reduction primitive. It supports two
scope models:

- `result=Join(...)` without `scope` waits for workflow-wide quiescence;
- a join with explicit `scope` creates one isolated barrier for each activation
  of the named scope node.

Current shape:

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

The workflow-wide form follows these execution rules:

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
Contribution order follows runtime arrival order.

Reducer tasks use normal binding, context injection, scheduling limits, and
failure propagation. Their raw returns are recorded in `WorkflowRun.outputs`.
Reducer-less joins add no output entry.

The reserved `result=Join(...)` remains terminal. A terminal scoped join requires
exactly one activation of its scope; repeated scope families should feed a
separate workflow-wide result join.

Join behavior composes with yield placement:

- `yield -> sub_workflow(...)` creates several independent child workflow executions
- `sub_workflow(yield -> ...)` creates coupled internal branches that may converge through `Join`

### Activation-Scoped Mid-Graph Joins

`Join` outside `result` uses the same public surface with an explicit `scope`.
The implemented model is:

- each activation of the scope node defines one branch family
- generator exhaustion closes further emission from a generator scope
- the join waits for all descendants in that family to settle
- only descendants routed to the join contribute values
- the preserved owner branch runs the reducer and continuation

This keeps dynamic branch cardinality compatible with joins without forcing a
statically paired split-and-join model. Distinct scopes may nest, and concurrent
activations of the same mid-graph scope remain isolated. Recursive re-entry into
the same join scope on one branch is rejected.

## Dynamic Execution

**Status: implemented for explicit `Expand(builder)` and self-routed
`Fragment` materialization. Callable `next`, lifecycle continuations, graph
introspection, and expansion budgets remain deferred.**

Dynamic execution extends the graph at runtime.

The graph evolution model is append-only.

That means Elan may materialize new continuation steps at runtime, but it does not rewrite already-materialized nodes or reroute already-scheduled execution.

Expansion is also controlled at the workflow level.

A workflow may explicitly allow or forbid dynamic expansion inside its own scope.

Policy shape:

```python
from elan import Workflow, WorkflowPolicy


Workflow(
    "dynamic_workflow",
    policy=WorkflowPolicy(allow_runtime_expansion=True),
    start=...,
    result=...,
)
```

This matters for both execution and validation:

- it gives users a clean way to disable expansion in sub-workflows
- it lets Elan reject `Expand(...)` statically when expansion is not allowed in that workflow

Dynamic expansion belongs to `next`.

The initial contract uses the explicit `Expand(...)` form only:

```python
from elan import Expand, Fragment, Node, Workflow, WorkflowPolicy


def build_dependencies(plan: Plan) -> Fragment:
    ...


workflow = Workflow(
    "dynamic_example",
    policy=WorkflowPolicy(allow_runtime_expansion=True),
    start=Node(
        run=create_plan,
        next=Expand(build_dependencies),
    ),
    publish=publish,
)
```

The builder is orchestration code, not a scheduled `Task`. It builds from the
expanding node's emitted value and returns exactly one `Fragment`; returning a
bare `Node`, `Workflow`, or union of structural forms is outside the initial
contract.

The accepted fragment semantics are:

- a fragment declares one entry node;
- its nodes own their complete routing, including edges to other fragment nodes
  and existing nodes in the static graph;
- the current branch enters the fragment through its declared entry;
- a fragment path whose node has no `next` terminates normally;
- expansion creates no implicit continuation or barrier;
- synchronization remains explicit through `Join`.

Appending a fragment is atomic. The runtime first assigns run-local identity,
constructs the candidate combined graph, and validates that graph. Only a valid
candidate is committed to `GraphState` and scheduled. Rejection leaves the
materialized graph unchanged.

The structural guardrails for dynamic execution are:

- append-only materialization
- no rewriting of already materialized nodes or routes
- one valid combined graph after each atomic append
- run-local namespacing isolates concurrent activations of the same expansion
- a fragment owns its entry and all outgoing routes
- expanded descendants inherit any active join-scope membership
- dynamic fragments may reference existing static nodes, but may not mutate them

Bare callable `next` and a `then`/`finally`-style expansion continuation are
explicitly deferred. The initial `Expand` contract does not reserve their
syntax or imply their eventual semantics.

The implemented decisions are:

- `Fragment(start=..., **nodes)` uses Workflow-like declarations but has no
  workflow name, context, policy, or local result boundary;
- builders are synchronous raw callables with one typed positional parameter
  and a declared `-> Fragment` return;
- builders receive the emitted packet after `bind_output`, while the original
  packet enters the fragment;
- every invocation is namespaced independently without mutating the returned
  `Fragment`;
- targets resolve lexically from current fragment to enclosing fragments to the
  original static workflow;
- fragments may contain local scoped joins and nested `Expand` sites;
- the candidate graph and join definitions commit atomically before entry
  scheduling;
- materialized tasks and reducers use normal output recording, while builders
  and graph topology are not added to `WorkflowRun`;
- no declaration-time reachability analysis, cross-edge type analysis,
  recursion-depth limit, or total-materialization budget is included.

## Cycles

**Status: partial scaffolding. Static-cycle detection and the
`WorkflowPolicy.allow_cycles` gate exist. Safe executable recurrence, visit
budgets, time budgets, and cycle-specific observability do not.**

Static cycles are part of the graph language.

They model declared recurrence.

Dynamic expansion and static cycles solve different problems:

- static cycles express recurrence in the declared graph
- dynamic expansion expresses graph growth at runtime

Cycle use is controlled through workflow policy.

Current policy shape:

```python
from elan import Workflow, WorkflowPolicy


Workflow(
    "agent_loop",
    start=...,
    result=...,
    policy=WorkflowPolicy(allow_cycles=True),
)
```

Current rule:

- cycles are invalid unless the workflow policy allows them

Enabling the flag currently bypasses static-cycle rejection; it does not provide
safe termination. The remaining intended rules are:

- allowed cycles remain subject to graph and type validation;
- cycle safety is enforced through runtime budgets rather than an implicit
  iteration limit.

The runtime policy surface for cycle safety includes:

- cycle opt-in
- point-in-time graph budgets
- cumulative graph budgets
- time budgets

Policies are objects so they can be reused across workflow boundaries.

That allows one workflow to carry a top-level policy while a sub-workflow reuses the same policy object or applies a narrower one.

Static cycles and dynamic expansion use the same guardrail system, but they remain separate graph features.

## Structured Payloads

**Status: implemented. `@ref` is optional for binding and required only for
class-level field references.**

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

**Status: implemented for exclusive routing, static fan-out, conditional
multi-routing, and sync/async generator fan-out.**

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

Current constraints:

- ref-based `route_on` applies to exclusive routing;
- routing or yielding directly into an ordinary reserved `result=Node(...)` is
  unsupported after fan-out; use `result=Join(...)` to collect branches;
- all statically declared target ids must resolve inside the current workflow.

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

Current shape:

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

Current shape:

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

The planned config form serializes the same idea explicitly:

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

Current shape:

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

Current shape:

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

**Status: design only. No config parser or config-backed workflow model is
implemented.**

The design goal is for code, config files, and API payloads to share one workflow
model. The examples below are proposed serialization shapes, not accepted input
to the current package.

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
      name: $input.name
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

**Status: design only. No HTTP service or run-resource API is implemented.**

The proposed HTTP API accepts the same workflow spec directly.

The API exposes the same workflow model instead of introducing a different orchestration format for HTTP clients.

Candidate endpoints:

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
          "name": "$input.name",
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

The HTTP status, error, activation-history, and output-reference shapes remain
unresolved. They should be derived from the implemented `WorkflowRun` contract
rather than replacing it with unrelated semantics.

## Production Runtime Design Notes

**Status: exploratory design only. The current runtime is in-process and
in-memory. There is no server package, worker protocol, Taskiq backend,
persistence backend, deployment model, or durable run API.**

These notes capture production runtime direction beyond the core workflow
authoring model. They are proposals to evaluate, not commitments made by the
current implementation.

Design choices in this area should be evaluated against Elan's existing goals:

- workflows stay centered on explicit graph structure, routing, and result boundaries
- tasks stay plain Python, reusable, and decoupled from orchestration machinery
- runtime concerns should not leak into business logic
- simple local execution should remain simple
- the same workflow should be able to grow from local usage to production usage without being rewritten
- the model should work for data workflows, agent workflows, service orchestration, and mixed workloads

### Provisional Design Direction

#### Production Runtime Model

One prior proposal uses a server plus worker model with Taskiq as the first
execution backend. That choice has not been implemented or validated and should
be revisited against requirements before it becomes a dependency.

Elan owns:

- the logical activation queue
- workflow state
- branch progression
- routing
- joins
- context
- result recording
- scheduling decisions

Under that proposal, Taskiq runs selected activations outside the orchestrator
process.

#### Activation Execution Contract

Elan submits executable activations, not workflow graphs, to workers.

An activation call identifies:

- run
- workflow
- node
- branch
- activation
- task name
- attempt
- resolved arguments
- execution context needed by the task signature

Workers resolve stable task names to executable Python callables.
Task execution remains based on ordinary Python function signatures.
Workers report execution outcome, output or error, timing, worker identity, and backend task identity when available.

Elan remains responsible for recording completion and advancing routing, joins, context, and workflow result.

#### Task Identity And Registration

The current local registry derives a canonical key from the Python import path
and optionally accepts `@task(alias="...")`. Remote execution would require a
stable naming contract beyond that current local behavior.

The production proposal uses registered task names.
Elan should expose its own task identity and registration surface, but keep it close to the Taskiq and Celery mental model so developers can rely on familiar behavior.

Task names are Elan task names.
The first Taskiq backend maps Elan task names directly to Taskiq task names.

Tasks may be referenced locally by Python callable or remotely by stable name:

- `Node(run=extract_metadata)`
- `Node(run="content.extract_metadata")`

The default remote task name could continue to derive from the Python import
path. A dedicated explicit-name surface is not implemented; the current public
override is `alias`:

- `@task(alias="content.extract_metadata")`

Workers register the task names they can execute.
The orchestrator should not need to import task implementation code just to dispatch remote activations by name.

#### Result And Value Reference Model

This section describes a proposed remote value-reference model. It is distinct
from the implemented `@ref` model-field registry and source namespaces.

Remote activation results could be represented as addressable value references by default.
Workers should not have to send full returned values back through the orchestrator unless the workflow runtime needs to materialize them.

Elan should distinguish:

- activation output, which is the value produced by one node execution
- activation outcome, which includes success, failure, cancellation, output reference, error reference, and observed type metadata
- workflow result, which is the explicit value exported by the workflow definition

The orchestrator should mostly operate on references and metadata.
In a simple linear workflow, the output of one activation should be passable to the next activation as a reference without loading the full value into orchestrator memory.

When Elan needs a value to evaluate workflow semantics, it should be able to resolve only the part it needs.
This applies to routing, binding, joins, result materialization, and later observability.

Refs are the public and internal abstraction for this addressing model.
A `Ref` is an accessor into a runtime value source, not just a marker for where a value came from.
Evaluating a ref should resolve the narrowest required value or metadata supported by the current backend.

Examples of things refs should be able to address:

- a field or path inside an upstream output
- selected context or workflow input fields
- observed output type metadata
- failure or exception type metadata

This keeps task code ordinary while allowing distributed execution to keep large values in the data plane instead of the orchestration control plane.

#### Activation Status Model

Current local activations use `queued`, `running`, and `settled`. A production
outcome model would need to distinguish:

- queued
- running
- succeeded
- failed
- cancelled

`running` means the activation has been handed to the execution backend.

#### Persistence Boundary

No run state is currently persisted. A durable runtime would need to persist at
least:

- run identity
- workflow identity
- workflow input
- workflow result
- branch state
- branch context
- activation state
- activation input
- activation output reference or error reference
- attempt count
- basic timestamps

## Open Production Capability Topics

These are practical capability areas that still need refinement.
They should be specified from requirements, use cases, and Elan's design goals rather than from a preferred infrastructure shape alone.

### Deployments

Deployments are the topic of how a workflow definition becomes a repeatable way to run something.

Requirements to satisfy:

- direct `Workflow.run(...)` must remain enough for local and embedded usage
- the same workflow definition should be reusable in more than one runtime setting
- runtime settings should not pollute task bodies or graph structure
- a repeatable run target should have a stable name or identity
- deployment should leave room for local runs, process workers, containers, remote execution, scheduled runs, and manual/API-triggered runs
- operational defaults such as input defaults, tags, retry policies, timeouts, schedules, or worker targeting should have a place if those features exist
- deployment should not force users into a server/control-plane model for simple usage

Shapes to evaluate:

- no deployment object
- lightweight deployment metadata
- Python deployment object
- config-defined deployment
- registered runtime deployment
- server-side deployment resource

Questions to refine:

- what is the minimum useful deployment concept for Elan?
- what belongs to a workflow definition versus a deployment?
- should one workflow support multiple deployments with different inputs, schedules, or environments?
- how much should Elan know about Docker, Kubernetes, workers, schedules, or APIs?

### Reliability Controls

Reliability controls are the topic of making workflow execution predictable when tasks fail, hang, or need to be stopped.

Requirements to satisfy:

- failure behavior should be explicit enough that workflow authors can reason about it
- retries should not require task code to know about orchestration policy
- timeouts and cancellation should be expressible without wrapping task business logic
- policies should work for linear workflows, branched workflows, and composed workflows
- branch failure behavior should be understandable: fail the branch, fail the workflow, retry the node, or continue through an explicit path
- policies should not make simple workflows verbose

Shapes to evaluate:

- node-level policies
- workflow-level defaults
- deployment-level defaults
- named reusable policies
- failure routing as part of the workflow graph
- failure handling as runtime policy outside the graph

Questions to refine:

- where should reliability policy live by default?
- should failure behavior be graph-visible or runtime-only?
- how cancellation propagates across branches and child workflows
- what the default failure behavior should be
- how retries interact with non-idempotent task side effects
- what retry, cancellation, and timeout behavior belongs to Elan versus Taskiq?

### Durable Execution

Durable execution is the topic of preserving workflow progress beyond one uninterrupted Python process.

Requirements to satisfy:

- a run should be able to survive process loss if durability is enabled
- resumability should not require task business logic to implement its own checkpoint system
- long-running workflows should be able to wait without occupying a running task forever
- durability must make branch and activation state recoverable enough to continue correctly
- the model should distinguish safe replay/resume from re-running side-effectful tasks blindly
- durability should support agent and human-in-the-loop workflows without turning every workflow into an agent runtime

Shapes to evaluate:

- in-memory only
- optional persistence backend
- persisted run log
- checkpointed run state
- event-sourced execution history
- durable wait states

Questions to refine:

- what state must be persisted to resume safely
- whether durability is core runtime behavior or an optional backend
- how resumability interacts with task side effects
- what parts of the workflow model must become deterministic, if any

### Observability

Observability is the topic of understanding what happened during a workflow run and why.

Requirements to satisfy:

- users should be able to inspect a run without reconstructing behavior from logs alone
- branch and activation structure should be visible
- inputs and outputs should be traceable at node level when safe to record
- failures should point to the workflow node and execution attempt that failed
- dynamic routing and materialized graph growth should remain understandable after the run
- observability should support both debugging and production operation
- sensitive values should not be exposed accidentally

Shapes to evaluate:

- run timeline
- branch and activation view
- inputs and outputs per node
- logs and metadata
- artifacts
- lineage records
- search/filter by workflow, run, and state

Questions to refine:

- what the canonical runtime event model should be
- what should be visible by default versus opt-in
- whether lineage and artifacts are first-class concepts or derived records
- how observability should represent branches, joins, retries, and runtime expansion

### Production Runtime Refinements

Production runtime refinements are the remaining questions around the server, worker, and backend execution model after the first Taskiq-backed direction.

Requirements to satisfy:

- local library usage must remain valid
- production usage should have a clear path beyond `await workflow.run(...)`
- execution should be able to move out of the authoring process when needed
- API-triggered runs should be possible without rewriting workflows
- workers should execute task calls based on stable task names and resolved function signatures
- Elan should be able to schedule queued activations itself, including future policies such as waiting-time based priority
- the execution backend should not become the durable source of truth for workflow progress
- the runtime model should leave room for self-hosted operation before any cloud-specific assumptions
- the production model should not make the core authoring API feel like a scheduler DSL

Questions to refine:

- what production story should exist before cloud is considered?
- what should be possible with only the Python package versus the server package?
- what is the minimal activation message passed from Elan to Taskiq?
- how should workers register or advertise executable task names?
- how much status metadata belongs in the activation execution contract?
- how should Elan-owned queue priority map onto Taskiq and broker-specific capabilities?

### Composition

Local composition is already implemented through `Node(run=child_workflow)`, an
explicit child result boundary, compatible context inheritance, and inherited
workflow policy. The remaining production topic is how that relationship is
represented across deployment, durability, failure, and observability
boundaries.

Requirements to satisfy:

- preserve the implemented result, input, context, and policy contracts
- composition should work with deployment, reliability, durability, and observability concerns
- composition should not become a shortcut for hiding arbitrary orchestration side effects

Shapes to evaluate:

- nested production run identities
- inline versus separately deployed child execution
- shared versus isolated persistence and retry scopes
- workflow fragments as a separate future feature

Questions to refine:

- how parent and child workflow runs are represented
- how composition appears in observability and failure handling
- whether a child can be deployed or versioned independently without changing
  local composition semantics

### Practical Use Cases

Practical use cases are the topic of grounding design choices in workflows people actually want to build.

Requirements to satisfy:

- use cases should pressure the API instead of merely demonstrating it
- examples should cover data workflows, agent workflows, and mixed workloads
- scenarios should reveal which features are actually necessary
- use cases should identify where durability, reliability, observability, or human-in-the-loop become unavoidable
- examples should stay concrete enough to prevent generic platform design

Candidate scenarios:

- document or content publishing pipeline
- customer onboarding or approval workflow
- support triage and escalation
- ETL plus enrichment plus notification
- human-reviewed agent workflow
- multi-step research or report generation workflow
- incident investigation workflow

Questions to refine:

- which use cases should become canonical examples
- which use cases require durability or human-in-the-loop support
- which use cases are too broad for the first production runtime design pass
- which use cases can be supported with the current core plus small extensions

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
