# Implementation Design

This note continues the interface and architecture work at the engine-internals level.

It is intentionally iterative. It should only contain concepts that have actually been discussed and accepted, plus the problematics that still need resolution around them.

This document is not a speculative full-engine blueprint. It should not invent runtime structures ahead of the design process.

This document should be read after:

- [architecture.md](./architecture.md)
- [interface_design.md](./interface_design.md)
- [guardrails.md](./guardrails.md)

## How to read this doc

Each top-level section corresponds to one internal concept or abstraction that has been explicitly discussed.

For each concept, this doc records only:

- what problem it exists to solve
- what functional responsibility it owns
- what boundary it must preserve
- what adjacent concepts it implies
- what remains unresolved

Anything beyond that belongs in later notes once the corresponding decisions are actually made.

## Branch

### Problematic

Elan needs a way to describe one execution flow through a workflow without collapsing workload data, scheduler state, synchronization state, and routing history into a single holder object.

This is especially important because Elan must support:

- branching and fan-out
- dynamic expansion
- nested workflow scopes
- static cycles

Without a dedicated abstraction, those concerns tend to collapse into an overloaded runtime carrier similar to `DataHolder`, where business payload and orchestration state become entangled.

### Functional responsibility

`Branch` is the charting abstraction for one execution flow.

Its responsibility is to describe how a flow moves through the materialized workflow graph over time.

For now, a branch is understood to own three things:

- past execution lineage
- current position
- branch-local materialized continuation

### Boundary

`Branch` is descriptive, not operative.

It exists to support:

- routing
- progress tracking
- cycle disambiguation
- runtime introspection and debugging

It does not exist to be the schedulable work item.

A branch must not become the place where unrelated runtime concerns accumulate. In particular, it must not own:

- workload payload
- bound inputs
- scheduler readiness
- waiting conditions
- synchronization state
- backend or transport state

### What each owned part means

#### Past execution lineage

The lineage records the ordered traversal history of the flow.

Its purpose is to make execution history explicit and unambiguous, especially when the same node can be visited multiple times through cycles or recurrence.

#### Current position

The current position describes where the execution flow currently is in graph terms.

This is a graph location, not a scheduler state. It says where the branch is, not whether it is runnable, running, blocked, or settled.

#### Branch-local materialized continuation

The branch-local materialized continuation is the visible continuation already known for that branch.

This is not "the whole future graph". It is the part of the continuation that is already materialized and therefore available to routing and progression.

That wording is important because Elan supports dynamic expansion. A branch may only know part of what comes next, and that visible continuation may grow over time.

### Adjacent concepts implied by Branch

Defining `Branch` this way implies that other responsibilities must live elsewhere, especially:

- workload transport
- schedulable execution state
- synchronization ownership
- global run state

The most immediate adjacent concept is `Activation`.

### Unresolved points

The following points are intentionally still open:

- the exact identity model of a branch
- how a branch relates to nested workflow scopes
- how branch lineage records fork points
- how branch-local continuation is represented internally
- whether branch ancestry and synchronization family identity are the same concept or separate ones

## Activation

### Problematic

If `Branch` is descriptive only, Elan still needs an operative runtime abstraction that represents schedulable progress through the execution schedule.

This is the missing concept between:

- the business-logic task definition
- the descriptive branch
- the concrete `asyncio.Task` used once execution is launched



### Functional responsibility

`Activation` is the scheduler-owned operative abstraction adjacent to a branch.

Its responsibility is to represent one schedulable execution state for one branch at one current position.

An activation sits one step above `asyncio.Task`:

- before launch, it exists as scheduler state
- during execution, it may be backed by an `asyncio.Task`
- after completion, it records the settled outcome that allows progression to continue

### Boundary

`Activation` is operative, not descriptive.

It exists to support:

- scheduler queues and readiness transitions
- launch of concrete execution
- lifecycle tracking from queued to settled
- handoff from scheduling to execution and back to routing

It is not:

- the `@task` business logic definition
- the branch itself
- the workload payload itself

### Relationship to Branch

The current accepted relationship is:

- `Branch` explains the execution flow
- `Activation` carries the current schedulable state for that flow

This means branch progression and scheduler progression are related, but they are not the same thing and should not be represented by the same object.

### Adjacent concepts implied by Activation

Defining `Activation` implies at least these other concepts, even though they are not designed yet:

- a workload carrier or workload reference
- a scheduler state model
- a concrete runtime execution handle
- a settled-result handoff back into routing

### Unresolved points

The following points are intentionally still open:

- the minimal fields of an activation
- whether an activation directly owns a workload reference or points to a separate carrier
- how much of the current position is duplicated in the activation versus referenced from the branch
- whether retries create new activations or are multiple states of the same activation
- whether synchronization gates are referenced by activations or managed separately by the scheduler

## Barrier

### Problematic

Elan needs a runtime-owned synchronization concept for cases where multiple execution flows must settle before continuation can proceed.

This need appears structurally in:

- fan-in after fan-out
- workflow `result`
- later mid-graph joins
- nested workflow completion boundaries

Without a dedicated synchronization abstraction, waiting semantics tend to leak into other objects such as branches, activations, or payload carriers.

### Functional responsibility

`Barrier` is the synchronization abstraction.

At this stage, its role is defined only at the highest level:

- it exists to synchronize multiple execution flows
- it determines when continuation may resume after that synchronization point

That is enough to justify it as a first-class runtime concept, but not enough yet to specify its exact mechanics.

### Boundary

`Barrier` is runtime-owned coordination state.

It is not:

- a business-logic task
- a branch
- an activation
- a payload carrier

Its existence should prevent synchronization logic from being spread across unrelated abstractions.

### Adjacent concepts implied by Barrier

Even in this intentionally minimal form, `Barrier` implies future relationships with:

- branch families
- activation settlement
- scheduler waiting semantics
- workflow scope boundaries
- join or result continuation

### Unresolved points

The following points are intentionally deferred:

- what exactly a barrier tracks
- whether it waits on branches, activations, packets, or settled outputs
- how barrier membership is established
- whether barriers are scope-local, branch-family-local, or both
- how barriers interact with retries
- how barriers interact with cycles
- how barriers interact with dynamic expansion
- whether `result` is a specialized barrier or merely uses the same underlying idea

## Progression Loop

### Problematic

Elan needs one explicit engine progression loop before it can define scheduler state, wait state, or queue mechanics.

Without that loop, internal runtime structures become arbitrary because there is no shared statement of how one workflow execution actually moves forward over time.

The first step is the simplest case:

- one workflow
- one branch
- one linear continuation
- no synchronization
- no dynamic expansion
- no cycles

That gives the engine one baseline progression model before branching and waiting semantics are introduced.

### Functional responsibility

The progression loop is the engine-level process that advances a workflow from:

- initial start

through:

- activation creation
- execution
- post-execution progression

until:

- no continuation remains

In the simple linear case, its responsibility is to:

- seed the first branch and activation from `start`
- execute one activation
- apply post-execution node behavior
- create the next activation before the current one is fully settled
- repeat until the branch reaches its end

### Boundary

The progression loop coordinates runtime concepts.

It is not itself:

- a scheduler queue
- a branch
- an activation
- a synchronization primitive

Its role is to define how those concepts interact in time.

In particular, this section only defines the simple linear loop.

It does not yet define:

- branching
- synchronization
- dynamic expansion
- cycles
- retries
- failure propagation

### Simple linear progression

The simple linear progression loop is:

1. resolve the workflow `start` node
2. create the initial branch
3. create the initial activation
4. enqueue that activation
5. dequeue one activation from the ready queue
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
    - enqueue that next activation
16. only after the continuation is enqueued is the previous activation fully settled
17. repeat until no continuation remains

Workflow completion in the simple linear case is reached when:

- no activation is ready
- no activation is running
- and the branch has no remaining continuation

### Why continuation must be enqueued before settlement

The loop must not fully settle an activation before its continuation has been materialized.

Otherwise the engine can observe a false terminal state:

- no ready activation
- no running activation
- next activation not enqueued yet

That creates a race where the workflow appears complete before progression has actually continued.

So in the simple linear case:

- task completion
- post-execution handling
- continuation creation

belong to one progression transaction

and only after that transaction is complete is the activation fully settled.

### Adjacent concepts implied by the progression loop

Even in the simple linear case, this loop implies:

- ready versus running activation state
- a settled activation outcome
- a branch update step after continuation resolution
- a workflow completion check that happens after continuation materialization

The next complexity layers build on top of this baseline:

- branching
- synchronization
- dynamic expansion
- cycles

### Unresolved points

The following points remain open:

- the exact runtime states of an activation between ready and fully settled
- the exact storage location of raw versus adapted node output
- how the loop is represented in concrete scheduler state
- how non-success outcomes modify progression
- how the linear loop generalizes once branching is introduced

## RunState And WorkflowRun

### Problematic

Elan needs one internal source of truth for a workflow run without making the public `WorkflowRun` object itself carry all mutable engine responsibilities.

At the same time, the public API already establishes `WorkflowRun` as the user-facing run object.

So the engine needs a clean relation between:

- internal mutable run truth
- public run inspection

### Functional responsibility

`RunState` is the internal mutable source of truth for one workflow run.

Its role is to own the runtime state that the engine mutates while the workflow progresses.

`WorkflowRun` is the public object that exposes run information to the user.

Its role is to present the externally meaningful view of the run without becoming a second source of truth.

### Boundary

`RunState` is engine-owned.

It is not part of the public interface.

`WorkflowRun` is public.

It must not become the place where internal engine mutation, queue bookkeeping, and progression mechanics are designed directly.

The accepted relation is:

- `RunState` is the internal truth
- `WorkflowRun` wraps or references that truth
- the engine mutates `RunState`
- `WorkflowRun` exposes selected run information derived from it

This avoids two competing representations of the same run.

### Minimum owned state

At the current level of design, `RunState` is expected to own at least:

- run identity
- workflow definition reference
- workflow input
- global run status
- branch registry
- activation registry
- barrier registry
- final result
- policy reference
- error or cancellation state

The exact field layout remains open.

### Unresolved points

The following points remain open:

- the exact public surface of `WorkflowRun`
- whether `WorkflowRun` exposes live views or copied snapshots
- how much settled execution history belongs in `RunState`
- whether traces and introspection data live in `RunState` or in a separate structure

## Scheduler State

### Problematic

The progression loop needs an operative scheduling view of the run.

That view must preserve the queue-driven shape without reintroducing an overloaded runtime carrier.

### Functional responsibility

`SchedulerState` is the operative scheduling view.

Its role is to track which activations are:

- ready
- running
- settled

This is the part of the engine that supports:

- dequeueing runnable work
- tracking launched execution
- observing completion
- deciding when the run is quiescent

### Boundary

`SchedulerState` is not the full run truth.

It is the operative scheduling index over runtime entities already owned elsewhere.

The accepted relation is:

- `RunState` owns the authoritative runtime entities
- `SchedulerState` tracks their scheduling status

So scheduler state should hold activation ids or references, not become a duplicate store for all run information.

### Shape

The intended first shape is:

- ready queue
- running set
- settled set

This is the minimal scheduling structure needed for the simple progression loop.

Additional waiting or blocked structures may appear later once synchronization and richer waiting semantics are designed.

### Adjacent concepts implied by SchedulerState

Defining `SchedulerState` this way implies:

- a ready activation creation step
- a running activation registration step
- a settled activation handoff back into progression
- a quiescence check that depends on scheduler state without replacing run truth

### Unresolved points

The following points remain open:

- the exact queue discipline
- whether scheduler state stores ids or direct references
- whether post-execution progression needs its own intermediate scheduling set
- how waits and barriers are indexed relative to scheduler state
- how cancellation and time budgets are reflected in scheduler state

## Current state of the design

At this stage, the following internal abstractions are defined strongly enough to live in this document:

- `Branch`
- `Activation`
- `Barrier` as a necessary but still underspecified synchronization abstraction
- the simple linear `Progression Loop`
- `RunState`
- `SchedulerState`

Everything else should remain out of this file until it is discussed at the same level of precision.
