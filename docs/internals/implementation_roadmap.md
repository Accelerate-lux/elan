# TDD Feature Roadmap From The Current Runtime Foundation

## Summary

The current runtime foundation is sufficient to stop refactoring internals and switch to feature delivery under strict TDD. The execution stack is now in the right shape:

- `Workflow` is a thin public definition/entrypoint
- `Orchestrator` owns run progression
- `Scheduler` owns activation execution/settlement
- `RunState` and `SchedulerState` are passive state containers
- `GraphState` is the run-local graph surface needed for later expansion
- `WorkflowRun` now exposes:
  - `result`: exported result, or terminal fallback
  - `outputs`: execution log grouped by task name

From here, all work proceeds feature-by-feature in interface order, with each feature implemented through a red/green/refactor loop and grounded in the current runtime objects rather than adding logic back into `Workflow`.

## TDD Working Model

For every feature phase, use this exact loop:

1. Add or update one small happy-path test in `tests/test_public_api.py`.
2. Add focused phase tests in the dedicated feature file.
3. Run the smallest failing subset first.
4. Implement the minimum runtime change needed to pass.
5. Refactor only after green, keeping behavior locked by the tests.
6. Update docs for that feature in the same slice when the public behavior changes.

Rules for the implementation work:
- `Workflow` stays thin.
- New behavior lands in `Orchestrator`, `Scheduler`, binding/routing helpers, or new private runtime helpers.
- Public API changes are always accompanied by:
  - `test_public_api.py`
  - at least one focused phase test file
  - doc updates when user-visible behavior changes

## Implementation Order

### 1. Restore the public smoke surface
Reintroduce `tests/test_public_api.py` as the small happy-path contract file.

Scope:
- one or two smoke tests per currently supported public behavior
- no edge-case accumulation
- used as the first red/green surface for every later feature

Keep the current split phase files as the real deeper spec:
- `test_core_execution.py`
- `test_binding_and_adaptation.py`
- `test_registry_and_declaration.py`
- `test_structured_payloads.py`

### 2. Richer `Node.output`
First new feature slice.

Implementation goal:
- expand `Node.output` beyond the current simple string/list mapping surface
- keep it as output adaptation only, not routing logic

Test work:
- smoke test in `test_public_api.py`
- deeper cases in `test_binding_and_adaptation.py`

Acceptance:
- mapped outputs still preserve raw task output in `run.outputs`
- richer output adaptation composes cleanly with existing binding rules
- no changes leak into `Workflow`

### 3. `Node.input`
Second feature slice.

Implementation goal:
- explicit input adaptation for downstream tasks
- done in the binding/orchestration layer, not inside tasks

Test work:
- one public smoke example in `test_public_api.py`
- focused cases in `test_binding_and_adaptation.py`

Acceptance:
- explicit input mapping overrides default automatic binding for that node
- binding failures stay narrow and explicit
- activation progression still flows through `Orchestrator` and `Scheduler`

### 4. Structured payload binding and `@el.ref`
Third slice.

Implementation goal:
- keep current Pydantic payload behavior
- add registered ref participation where the public interface already expects it

Test work:
- smoke case in `test_public_api.py`
- deeper cases in `test_structured_payloads.py`

Acceptance:
- structured payload binding remains stable
- ref registration and lookup are covered explicitly
- no config/API parity work yet beyond what is needed for Python behavior

### 5. Branching forms
Fourth slice.

Implementation goal:
- move from the current single-string `next` to actual branching forms in interface order
- branch creation stays orchestrator-owned
- scheduler continues to execute/settle activations only

Test work:
- new `tests/test_routing_and_branching.py`
- one public smoke branching example in `test_public_api.py`

Acceptance:
- branch creation is explicit and testable
- branch position is tracked by node name only
- no feature logic is bolted into `Workflow.run()`

### 6. Terminal `Join` on `result`
Fifth slice.

Implementation goal:
- first implementation only
- restricted to reserved `result`
- no mid-graph join work

Test work:
- new `tests/test_join_result.py`
- one public smoke workflow with `result=Join(...)`

Acceptance:
- join waits on workflow-scope completion as currently designed
- exported value lands in `WorkflowRun.result`
- execution history still lands in `WorkflowRun.outputs`

### 7. Context and `after`
Sixth slice.

Implementation goal:
- workflow-level context model
- node context preparation
- post-execution updates through `after`
- all state changes go through run/orchestration state, not ad hoc payload mutation

Test work:
- new `tests/test_context_and_after.py`
- one public smoke case in `test_public_api.py`

Acceptance:
- branch-local context behavior is covered
- unknown or invalid writes fail clearly
- post-execution timing is explicit in tests

### 8. Composition
Seventh slice.

Implementation goal:
- `Node(run=child_workflow)`
- parent receives child exported result, not full child `WorkflowRun`

Test work:
- new `tests/test_composition.py`
- one public smoke composition example in `test_public_api.py`

Acceptance:
- child workflows run through the same runtime stack
- result boundary is explicit and stable
- no special-case composition path in `Workflow`

### 9. Dynamic expansion and cycles
Eighth slice.

Implementation goal:
- `Expand(...)`
- callable `next`
- append-only graph growth through `GraphState`
- policy-controlled cycles and expansion behavior

Test work:
- new `tests/test_dynamic_execution.py`
- later a dedicated cycles/policy file if the surface grows enough

Acceptance:
- dynamic graph changes happen against `RunState.graph`
- branch position remains name-based against the materialized graph
- runtime checks stay in orchestrator/scheduler/runtime helpers, not public API objects

## Test File Plan

Keep or restore these files as the long-term structure:

- `tests/test_public_api.py`
  - small happy-path public smoke suite
- `tests/test_core_execution.py`
- `tests/test_binding_and_adaptation.py`
- `tests/test_registry_and_declaration.py`
- `tests/test_structured_payloads.py`
- `tests/test_routing_and_branching.py`
- `tests/test_join_result.py`
- `tests/test_context_and_after.py`
- `tests/test_composition.py`
- `tests/test_dynamic_execution.py`

Usage rule:
- `test_public_api.py` proves the public surface stays ergonomic
- phase files carry the real behavioral spec and edge coverage

## Assumptions And Defaults

- `test_public_api.py` is restored as the small end-to-end smoke surface.
- Feature work follows the interface-order sequence already established:
  - richer `Node.output`
  - `Node.input`
  - structured payloads / refs
  - branching
  - terminal `Join`
  - context / `after`
  - composition
  - dynamic expansion / cycles
- Docs are updated in the same feature slice when public behavior changes.
- The current runtime layering is considered stable enough to build features on top of:
  - `Workflow`
  - `Orchestrator`
  - `Scheduler`
  - `RunState`
  - `SchedulerState`
  - `GraphState`
- No new feature work goes back into `Workflow.run()` except thin delegation changes.
