# AI Authoring

This guide is canonical context for coding agents and humans reviewing
AI-written Elan workflows.

!!! info "Capability status"
    The patterns below use the current **Available** API, except `Expand` and
    `Fragment`, which are **Experimental**. Direct registered-task invocation
    and declaration-only graph inspection are **Planned** and have no runnable
    syntax here.

## Mental model

- A `Task` registers typed business work.
- A `Node` configures that work and declares outgoing routes.
- A `Workflow` owns the stable graph, context model, policy, and result boundary.
- A `Join` synchronizes contributing branches and may reduce their values.
- An `Expand` builder maps one validated runtime value to one namespaced
  `Fragment` when the graph cannot be fully declared ahead of time.

Keep business work in tasks and control flow in declarations. A reviewer should
not need to inspect a task body to discover which node runs next.

## Canonical patterns

### Keep directly tested logic raw

```python
from elan import Node, Workflow, task


def normalize_name(value: str) -> str:
    return value.strip().title()


normalize_name_task = task(normalize_name)

workflow = Workflow(
    "normalize",
    start=Node(run=normalize_name_task),
)
```

Call `normalize_name(...)` in a unit test. The registered Task object is not
directly callable today.

### Make value sources explicit when they matter

Use `Binder[target]` with `Input`, `Upstream`, `Context`, or `Policy` when a
reviewer needs to see where a parameter originates. Default binding remains the
preferred form when one scalar or one typed model flows unambiguously.

### Match the routing form to the decision

- `next="target"` for one continuation
- `next=[...]` for fan-out
- `next={...}` with `route_on` for exclusive value dispatch
- `When(...)` for independent conditional routes
- `Join(...)` when descendant branches must converge

### Keep reducers deterministic

Join contribution order follows runtime arrival order. Sort values or use an
order-agnostic reduction unless completion order is deliberately constrained.

### Keep expansion builders declarative

An `Expand` builder must be synchronous, accept one annotated positional value,
declare `-> Fragment`, and return declarations. Put API calls, database writes,
LLM requests, and other business work in tasks before or inside the fragment.
Every workflow containing expansion must opt in with
`WorkflowPolicy(allow_runtime_expansion=True)`.

## Anti-patterns

- Hiding reviewer-relevant routing inside a task body
- Performing I/O or business work in an expansion builder
- Using raw dictionaries when an explicit typed model would clarify a boundary
- Writing a reducer that depends on sibling arrival order
- Enabling recursive expansion without a terminating condition
- Claiming retries, persistence, resume, remote workers, or MCP runtime
  operations exist
- Inventing syntax for direct Task calls or graph rendering

## Copyable `AGENTS.md` instructions

```markdown
## Authoring Elan workflows

- Keep typed business logic separate from orchestration declarations.
- When logic needs direct unit tests, retain the raw function and register it
  separately with `task(raw_function)`; registered Task objects are not directly
  callable in the current API.
- Put routes in `Node`, `When`, `Join`, and `Workflow`, not inside task bodies.
- Prefer a Workflow subclass for application code and the constructor for small
  examples or generated declarations.
- Use `Binder[target]` and Input/Upstream/Context/Policy references when the
  source of a value should remain explicit.
- Treat join contribution order as nondeterministic; sort or reduce
  order-independently.
- Use Expand only when a typed runtime value determines graph structure. Its
  builder must be synchronous declaration code with no I/O and return Fragment.
- Expansion requires WorkflowPolicy(allow_runtime_expansion=True), and recursive
  builders must provide their own terminating condition.
- Do not use or claim retries, persisted runs, remote workers, direct Task
  invocation, or declaration-only graph rendering. Check Elan's status page.
```

## Review checklist

1. Can each route be found in the declaration?
2. Are payload and context boundaries typed?
3. Are joins scoped to the intended activation?
4. Is reducer output deterministic across arrival orders?
5. Does every expansion builder terminate and avoid I/O?
6. Does the example use only capabilities with the documented maturity?

For exact semantics, read [Runtime Behavior](../reference/runtime-behavior.md).
