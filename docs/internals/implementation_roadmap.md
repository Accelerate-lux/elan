# Implementation Roadmap

This note records the post-foundation delivery plan for Elan.

The current runtime base is stable enough to build features on top of:

- `Workflow` as the thin public entrypoint
- `Orchestrator` as the run progression owner
- `Scheduler` as the activation execution and settlement owner
- `RunState` and `SchedulerState` as passive state containers
- `GraphState` as the run-local graph surface
- `WorkflowRun` with:
  - `result`
  - `outputs`

Future features extend this runtime model. New behavior does not go back into `Workflow.run()`.

## TDD Working Model

Every feature slice follows the same loop:

1. Add or update one happy-path smoke test in `tests/test_public_api.py`
2. Add focused tests in the dedicated phase test file
3. Run the smallest failing subset first
4. Implement the minimum runtime change to pass
5. Refactor only after green
6. Update docs in the same slice when public behavior changes

Implementation rules:

- `Workflow` stays thin
- new behavior lands in orchestration and runtime helpers
- public API changes always ship with tests and docs together

## Implementation Order

Restore `tests/test_public_api.py` first as the small public smoke surface.

Current baseline already exists for:

- simple `next`
- basic `Node.output`
- current structured payload binding

The next feature slices are:

1. `Node.input`
   Goal: add explicit input adaptation in the binding and orchestration layer.
   Tests: `tests/test_public_api.py` and `tests/test_binding_and_adaptation.py`

2. Extended structured payload and `@el.ref` support
   Goal: extend the current structured payload model with registered refs where the interface expects them.
   Tests: `tests/test_public_api.py` and `tests/test_structured_payloads.py`

3. Branching forms
   Goal: move from single-string `next` to explicit branching while keeping branch creation in the orchestrator.
   Tests: `tests/test_public_api.py` and `tests/test_routing_and_branching.py`

4. Terminal `Join` on `result`
   Goal: add the first join implementation, restricted to the reserved `result` node.
   Tests: `tests/test_public_api.py` and `tests/test_join_result.py`

5. Context and `after`
   Goal: add workflow context, node context preparation, and post-execution updates.
   Tests: `tests/test_public_api.py` and `tests/test_context_and_after.py`

6. Composition
   Goal: support `Node(run=child_workflow)` with explicit result boundaries.
   Tests: `tests/test_public_api.py` and `tests/test_composition.py`

7. Dynamic expansion and cycles
   Goal: add `Expand(...)`, callable `next`, append-only graph growth, and policy-controlled recurrence.
   Tests: `tests/test_public_api.py` and `tests/test_dynamic_execution.py`

## Test File Structure

Long-term test layout:

- `tests/test_public_api.py`
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

- `tests/test_public_api.py` is the small ergonomic public smoke surface
- phase files are the detailed behavioral spec

## Current Interface Notes

The current public run contract is:

- `WorkflowRun.result` is the exported reserved `result` value when present
- otherwise `WorkflowRun.result` falls back to the last terminal output
- `WorkflowRun.outputs` is the execution log grouped by task name

The current runtime constraints that later features must preserve are:

- branch position is tracked by node name
- node resolution happens against `RunState.graph`

Source of truth ordering:

- `interface_design.md` for the intended public model
- `implementation_design.md` for runtime layering
- `implementation_roadmap.md` for delivery order and TDD workflow
