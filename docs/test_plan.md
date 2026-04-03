# Test Plan

This document lists the tests Elan should have.

The list is ordered by complexity so the suite can grow without changing the overall structure of the plan.

Status:

- ✅ implemented
- ⬜ planned
- 🔒 reserved for a feature that does not exist yet

## Feature Breakdown

### Phase 1. Core Task Execution And Binding

This phase covers the smallest executable workflows: one task, simple chaining, automatic binding, explicit `bind_input` and `bind_output` adaptation, and the base `WorkflowRun` contract.

### Phase 2. Registry And Workflow Declaration

This phase covers task registration, canonical keys, aliases, workflow declaration shape, and basic graph construction errors such as unknown task references or invalid node references.

### Phase 3. Structured Payloads And Refs

This phase covers structured payload binding, `@el.ref`, named field access, workflow result boundaries, and how registered payloads participate in routing, context updates, and config/API references.

### Phase 4. Context And Post-Execution Updates

This phase covers workflow context models, `Node.context`, `after.context`, merge semantics, unknown-field rejection, timing rules, and branch-local context behavior before join or workflow completion.

### Phase 5. Routing And Branching

This phase covers first-pass exclusive branching, first-pass fan-out, first-pass `When(...)` conditional multi-routing, branch creation rules, route validation, string-only `route_on`, and the scoped behavior of sibling branches after routing decisions. Ref-based `route_on` stays deferred.

### Phase 6. Yield Fan-Out And Branch Completion

This phase covers `yield` as runtime fan-out, dynamic branch cardinality, downstream scheduling for yielded packets, branch-local execution scopes, and workflow completion behavior when yielded branches are still active.

### Phase 7. Composition And Result Boundaries

This phase covers `Node(run=child_workflow)`, child result export through `result`, input and context crossing workflow boundaries, and parent behavior while child workflows are executing.

### Phase 8. Join Behavior

This phase covers the first implementation of `Join`: terminal-only usage on `result`, contribution collection, reducer behavior, waiting on workflow scope completion, and non-contributing sibling branches.

### Phase 9. Dynamic Execution And Expansion

This phase covers callable `next`, `Expand(...)`, append-only graph growth, direct node/fragment/workflow expansion, continuation anchors through `then`, and incremental validation of materialized graph segments.

### Phase 10. Cycles And Policy Guardrails

This phase covers policy-controlled static cycles, dynamic expansion toggles, graph and time budgets, validation toggles, and the runtime boundaries that constrain recurrence and graph growth.

### Phase 11. Validation And Error Surfaces

This phase covers static graph validation, static type validation, semi-static runtime validation, and the failure surfaces that must stay narrow and explicit when workflows, routing, joins, or expansions are invalid.

### Phase 12. Config And API Parity

This phase covers the config/API representation of the Python model, including workflow definitions, refs, context ids, dynamic continuation shapes, and run/result payloads.

### Phase 13. Reserved Future Surfaces

This phase keeps space for deferred features that need their own test surface later, especially mid-graph joins, richer error handling behavior, and agent-specific workflow features.

## 1. One async task workflow

Status: ✅  
Source: [tests/test_public_api.py](/C:/Users/Hugod/Workspace/elan/tests/test_public_api.py)

What it tests:

- a registered async task can be used directly as a workflow start node
- `Workflow.run()` executes it successfully
- `WorkflowRun.outputs` stores the task output under the initial branch id and task name

## 2. One sync task workflow

Status: ✅  
Source: [tests/test_public_api.py](/C:/Users/Hugod/Workspace/elan/tests/test_public_api.py)

What it tests:

- a registered sync task can be used directly as a workflow start node
- `Workflow.run()` executes it successfully from the async runtime
- the run result has the same shape as in the async case

## 3. Two-task workflow with scalar binding

Status: ✅  
Source: [tests/test_public_api.py](/C:/Users/Hugod/Workspace/elan/tests/test_public_api.py)

What it tests:

- a workflow can chain one task to another through `next`
- a scalar output binds automatically to one downstream parameter
- `WorkflowRun.outputs` contains outputs for both tasks under the initial branch id

## 4. Two-task workflow with explicit output mapping

Status: ✅  
Source: [tests/test_public_api.py](/C:/Users/Hugod/Workspace/elan/tests/test_public_api.py)

What it tests:

- `Node.bind_output` can adapt one task output into a named payload
- the downstream task receives the mapped named argument
- mapped payloads bind by parameter name

## 5. Two-task workflow with output discard

Status: ✅  
Source: [tests/test_public_api.py](/C:/Users/Hugod/Workspace/elan/tests/test_public_api.py)

What it tests:

- output mapping can discard positions with `...`
- only selected values are forwarded
- the raw upstream output is still preserved in `WorkflowRun.outputs`

## 6. Tuple output binds positionally

Status: ✅  
Source: [tests/test_public_api.py](/C:/Users/Hugod/Workspace/elan/tests/test_public_api.py)

What it tests:

- tuple output binds to downstream parameters by position
- ordered values are passed as positional arguments

## 7. Tuple output arity mismatch fails clearly

Status: ✅  
Source: [tests/test_public_api.py](/C:/Users/Hugod/Workspace/elan/tests/test_public_api.py)

What it tests:

- tuple positional binding requires exact arity
- the runtime fails clearly instead of guessing

## 8. Tuple output type mismatch fails clearly

Status: ✅  
Source: [tests/test_public_api.py](/C:/Users/Hugod/Workspace/elan/tests/test_public_api.py)

What it tests:

- positional binding validates annotated downstream parameters
- incompatible values fail before task execution

## 9. List output stays opaque

Status: ✅  
Source: [tests/test_public_api.py](/C:/Users/Hugod/Workspace/elan/tests/test_public_api.py)

What it tests:

- list outputs are not auto-bound positionally
- a list may still flow as one opaque value into a single downstream parameter

## 10. Raw dict output stays opaque

Status: ✅  
Source: [tests/test_public_api.py](/C:/Users/Hugod/Workspace/elan/tests/test_public_api.py)

What it tests:

- raw dict outputs are not auto-unpacked
- a raw dict may still flow as one opaque value into a single downstream parameter

## 11. Raw dict output does not bind named parameters

Status: ✅  
Source: [tests/test_public_api.py](/C:/Users/Hugod/Workspace/elan/tests/test_public_api.py)

What it tests:

- raw dict output is not treated as a named payload
- a downstream task expecting named fields fails clearly without an explicit adapter or structured payload

## 12. Pydantic payload auto-unpacks

Status: ✅  
Source: [tests/test_public_api.py](/C:/Users/Hugod/Workspace/elan/tests/test_public_api.py)

What it tests:

- Pydantic model outputs are treated as structured payloads
- matching model fields bind downstream parameters by name automatically

## 13. Pydantic payload ignores extra fields

Status: ✅  
Source: [tests/test_public_api.py](/C:/Users/Hugod/Workspace/elan/tests/test_public_api.py)

What it tests:

- extra model fields do not break downstream binding
- only required matched fields are passed

## 14. Pydantic payload missing required field fails clearly

Status: ✅  
Source: [tests/test_public_api.py](/C:/Users/Hugod/Workspace/elan/tests/test_public_api.py)

What it tests:

- downstream required parameters must exist on the structured payload
- missing fields fail clearly

## 15. Pydantic payload passes through as one value

Status: ✅  
Source: [tests/test_public_api.py](/C:/Users/Hugod/Workspace/elan/tests/test_public_api.py)

What it tests:

- when the downstream task expects the model type itself, Elan passes the model instance through instead of unpacking it

## 16. Start task resolved by canonical key

Status: ✅  
Source: [tests/test_public_api.py](/C:/Users/Hugod/Workspace/elan/tests/test_public_api.py)

What it tests:

- a workflow can resolve its start task from the registry using the canonical key

## 17. Node task resolved by canonical key

Status: ✅  
Source: [tests/test_public_api.py](/C:/Users/Hugod/Workspace/elan/tests/test_public_api.py)

What it tests:

- `Node.run` can resolve a task from the registry using the canonical key
- downstream workflow nodes can also be declared by registered task name

## 18. Task resolved by alias

Status: ✅  
Source: [tests/test_public_api.py](/C:/Users/Hugod/Workspace/elan/tests/test_public_api.py)

What it tests:

- a workflow can resolve tasks by explicit alias
- alias resolution works for both `start` and downstream workflow nodes

## 19. Duplicate alias is rejected

Status: ✅  
Source: [tests/test_public_api.py](/C:/Users/Hugod/Workspace/elan/tests/test_public_api.py)

What it tests:

- the registry rejects alias collisions explicitly

## 20. Unknown task reference fails clearly

Status: ✅  
Source: [tests/test_public_api.py](/C:/Users/Hugod/Workspace/elan/tests/test_public_api.py)

What it tests:

- resolving an unknown canonical key or alias fails clearly

## 21. Raw callable is rejected

Status: ✅  
Source: [tests/test_public_api.py](/C:/Users/Hugod/Workspace/elan/tests/test_public_api.py)

What it tests:

- the runtime refuses to execute a raw undecorated callable

## 22. Initial workflow input is passed to the start task

Status: ⬜

What it tests:

- `workflow.run(**input)` binds named workflow input to the start task

## 23. Unknown next node fails clearly

Status: ⬜

What it tests:

- a workflow with `next=\"missing_node\"` fails explicitly instead of stopping or misrouting

## 24. Unsupported `next` shape fails clearly

Status: ⬜

What it tests:

- unsupported `next` forms fail with a clear error

## 25. Branching with `next` as `dict`

Status: ✅  
Source: [tests/test_routing_and_branching.py](/C:/Users/Hugod/Workspace/elan/tests/test_routing_and_branching.py)

What it tests:

- one node can route to one downstream branch from a named adapter payload
- one node can route to one downstream branch from a raw `dict`
- missing `route_on`, missing selector fields, unmapped values, and unknown targets fail clearly

## 26. Fan-out with `next` as `list`

Status: ✅  
Source: [tests/test_routing_and_branching.py](/C:/Users/Hugod/Workspace/elan/tests/test_routing_and_branching.py)

What it tests:

- one node can schedule multiple downstream branches
- sibling branches receive duplicated downstream payload
- outputs are grouped under distinct branch ids
- fan-out without reserved `result` returns `None`
- fan-out with reserved `result` is rejected until `Join` exists

## 27. Conditional multi-routing with `When(...)`

Status: ✅  
Source: [tests/test_routing_and_branching.py](/C:/Users/Hugod/Workspace/elan/tests/test_routing_and_branching.py)

What it tests:

- `When("field", "node")` routing from named payloads and raw `dict` outputs
- `When(Payload.field, "node")` routing from registered ref model outputs
- `When(condition, ["a", "b"])` conditional fan-out
- multiple independent matches, zero matches, and duplicate destinations
- missing fields, non-bool conditions, mixed `next` lists, unknown destinations, and reserved `result` rejection

## 28. Barriers and joins

Status: 🔒

What it should test:

- parallel branches can synchronize before the workflow continues
