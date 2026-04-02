# Implementation Design

This note continues the interface and architecture work at the engine-internals level.

It only records concepts that are already accepted or concrete enough to review. It is not a full engine blueprint.

Read this after:

- [architecture.md](./architecture.md)
- [interface_design.md](./interface_design.md)
- [guardrails.md](./guardrails.md)

## Branch

`Branch` is the descriptive execution path through the materialized workflow graph.

It currently owns:

- lineage
- current position
- branch-local visible continuation

It exists for routing, progress tracking, cycle disambiguation, and runtime introspection.

It is not:

- the schedulable work item
- the workload carrier
- scheduler state
- synchronization state

Open points:

- exact branch identity model
- relation to nested workflow scopes
- how lineage records fork points
- how branch-local continuation is represented
- whether branch ancestry and synchronization family identity are the same concept

## Activation

`Activation` is the schedulable execution unit adjacent to a branch.

For now, one activation corresponds to one node execution attempt for one branch at one current position.

It exists to support:

- ready/running/settled execution state
- launch of concrete runtime work
- handoff from execution back into progression

It is not:

- the branch itself
- the business-logic task definition
- the workload payload itself

Open points:

- minimal activation fields
- whether it owns a workload reference or points to one
- how much current-position data is duplicated versus referenced
- whether retries create new activations or reuse one activation
- how synchronization state is referenced from an activation

## Barrier

`Barrier` is the internal synchronization mechanism behind workflow `result` joins.

It exists to keep waiting semantics out of branches, activations, and payload carriers.

At the current level of design, it is intentionally narrow:

- it synchronizes the flows that contribute to workflow `result`
- it determines when workflow result continuation may resume

It is not yet a general fan-in or mid-graph join mechanism.

Open points:

- what exactly a barrier tracks
- whether it waits on branches, activations, packets, or settled outputs
- how membership is established
- how it interacts with retries, cycles, and dynamic expansion
- whether `result` is a specialized barrier or simply uses the same underlying idea

## Progression Loop

The progression loop defines how one workflow execution moves forward over time. It comes before scheduler mechanics.

The current baseline is the simple linear case:

- one workflow
- one branch
- one linear continuation
- no synchronization
- no dynamic expansion
- no cycles

The simple loop is:

1. resolve the workflow `start` node
2. create the initial branch
3. create the initial activation
4. enqueue that activation
5. dequeue one ready activation
6. resolve `input`
7. resolve `context`
8. build the task call
9. launch execution
10. wait for task completion
11. store the raw task outcome on the activation
12. apply `output`
13. apply `after`
14. resolve `next`
15. if a next node exists:
    - update the branch position
    - create the next activation
    - enqueue it
16. only then is the previous activation fully settled
17. repeat until no continuation remains

The key rule is that continuation must be enqueued before the previous activation is fully settled. Otherwise the engine can observe a false terminal state with no ready work, no running work, and no next activation yet materialized.

Open points:

- exact activation states between ready and fully settled
- where raw versus adapted node output is stored
- how non-success outcomes modify progression
- how the loop generalizes once branching is introduced

## RunState And WorkflowRun

`RunState` is the internal mutable source of truth for one workflow run.

`WorkflowRun` is the public run object.

The accepted relation is:

- `RunState` is the internal truth
- `WorkflowRun` wraps or references that truth
- the engine mutates `RunState`
- `WorkflowRun` exposes selected run information derived from it

This avoids two competing run representations.

At minimum, `RunState` is expected to own:

- run identity
- workflow definition reference
- workflow input
- global status
- branch registry
- activation registry
- barrier registry
- final result
- policy reference
- error or cancellation state

Open points:

- the exact public surface of `WorkflowRun`
- whether `WorkflowRun` exposes live views or snapshots
- how much settled execution history belongs in `RunState`
- where traces and introspection data live

## SchedulerState

`SchedulerState` is the operative scheduling view over the run.

It tracks activations as:

- ready
- running
- settled

So the intended first shape is:

- ready queue
- running set
- settled set

`SchedulerState` is not the full run truth. `RunState` owns the runtime entities; `SchedulerState` tracks their scheduling status.

Open points:

- exact queue discipline
- whether scheduler state stores ids or direct references
- whether post-execution progression needs its own intermediate state
- how waits and barriers are indexed relative to scheduler state
- how cancellation and time budgets are reflected in scheduler state

## Current State Of The Design

The following internal concepts are concrete enough to live in this document:

- `Branch`
- `Activation`
- `Barrier` as the internal mechanism behind workflow `result` joins
- the simple linear `Progression Loop`
- `RunState`
- `SchedulerState`

Everything else stays out until it is discussed at the same level of precision.
