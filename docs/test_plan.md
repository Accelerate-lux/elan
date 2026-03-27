# Test Plan

This document lists the tests Elan should have.

The list is ordered by complexity so the suite can grow without changing the overall structure of the plan.

Status:

- ✅ implemented
- ⬜ planned
- 🔒 reserved for a feature that does not exist yet

## 1. One async task workflow

Status: ✅  
Source: [tests/test_public_api.py](/C:/Users/Hugod/Workspace/elan/tests/test_public_api.py)

What it tests:

- a registered async task can be used directly as a workflow start node
- `Workflow.run()` executes it successfully
- `WorkflowRun` stores the task output under the task name

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
- the run result contains outputs for both tasks

## 4. Two-task workflow with explicit output mapping

Status: ✅  
Source: [tests/test_public_api.py](/C:/Users/Hugod/Workspace/elan/tests/test_public_api.py)

What it tests:

- `Node.output` can adapt one task output into a named payload
- the downstream task receives the mapped named argument
- mapped payloads bind by parameter name

## 5. Two-task workflow with output discard

Status: ✅  
Source: [tests/test_public_api.py](/C:/Users/Hugod/Workspace/elan/tests/test_public_api.py)

What it tests:

- output mapping can discard positions with `...`
- only selected values are forwarded
- the raw upstream output is still preserved in `WorkflowRun`

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

Status: 🔒

What it should test:

- one node can route to one of several downstream branches

## 26. Fan-out with `next` as `list`

Status: 🔒

What it should test:

- one node can schedule multiple downstream branches
- workflow completion waits for all active branches

## 27. Barriers and joins

Status: 🔒

What it should test:

- parallel branches can synchronize before the workflow continues
