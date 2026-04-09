# Type System Requirements

This document defines the requirements for Elan's validation and type system.

It is a requirements note, not an implementation plan.

The type system in Elan is broader than Python type checking alone. It must validate:

- graph integrity
- workflow contracts
- type compatibility
- runtime-materialized graph structure

The goal is to make workflow failures predictable and early without forcing Elan to behave like a full static analyzer for arbitrary Python.

## Core Principle

Elan validates workflow contracts, not arbitrary Python.

That means the validation system is responsible for the parts of the program Elan can reason about:

- task signatures
- task return types
- node adapters
- context schema
- workflow composition boundaries
- routing
- joins
- graph structure

Elan is not responsible for proving the correctness of arbitrary task internals.

## Validation Layers

The validation system must have three layers:

1. static graph validation
2. static type validation
3. semi-static runtime validation

These layers serve different purposes and stay conceptually separate.

## 1. Static Graph Validation

Static graph validation runs when the workflow definition is known.

It validates structural integrity independently of value types.

The system must detect at least:

- missing `start`
- missing `result`
- unknown `start` target
- unknown `next` target
- stray nodes that are never reachable
- invalid routing targets
- invalid use of `Join` outside the reserved `result` node
- invalid use of `Expand(...)` or callable `next` in workflows where expansion is not allowed
- cycles in workflows where cycles are not allowed
- `result` nodes that are not terminal
- child workflows that do not define a valid `result`

The validator also catches shape mismatches in workflow structure, for example:

- `route_on` used with an incompatible `next` form
- `When(...)` used where conditional multi-routing is not valid
- reserved workflow node ids used incorrectly

When cycles are allowed by workflow policy, static graph validation detects them and validates the graph as a cyclic workflow instead of rejecting the graph automatically.

Static graph validation fails fast and produces explicit errors.

## 2. Static Type Validation

Static type validation runs when the workflow shape is known and enough type information is available.

It validates compatibility between the declared workflow surfaces.

### Typed Surfaces

The static type system must reason over these surfaces:

- task input parameters
- task return annotations
- yielded item types
- workflow context model
- `Node.bind_input`
- `Node.bind_output`
- `Node.context`
- `route_on`
- `When(...)`
- `Expand(...)`
- `Node(run=child_workflow)`
- `result=Join(...)`

### Input Contracts

The validator must verify, when possible:

- that `Node.bind_input` provides values compatible with the target task parameters
- that automatic binding is valid for the receiving task
- that parent-to-child workflow boundaries are compatible

### Output Contracts

The validator must verify, when possible:

- that a task return annotation is compatible with `Node.bind_output`
- that positional output mapping matches tuple shape
- that discarded positions are valid
- that structured payload binding is compatible with downstream expectations

### Context Contracts

The validator must verify:

- that `Context.foo` refers to a valid field on the declared context model
- that `Node.context` writes only valid context fields
- that written values are compatible with the context field types

Unknown context fields must be invalid.

If post-execution context hooks are added later, they should follow the same field and type validation rules.

### Routing Contracts

The validator must verify:

- that `route_on="field"` points to a valid exposed field when that can be known statically
- that `route_on=Payload.field` refers to a valid field on a registered ref class
- that `When(Payload.field, ...)` refers to a valid boolean field

### Composition Contracts

The validator must verify:

- that a child workflow exposes a valid `result`
- that the child workflow's result type is compatible with the parent node that consumes it

### Dynamic Continuation Contracts

The validator must verify:

- that `Expand(...)` is used in a valid continuation position
- that `Expand(...)` and callable `next` are only used in workflows that allow expansion
- that cycles are only used in workflows that allow cycles
- that `then`, when present, refers to a valid existing node in the current known graph
- that the expansion builder input is compatible with the current node's exposed output when that can be known statically

If the expansion builder returns a fully materialized structure, Elan must validate that current structure as inserted:

- returned `Node`
- returned workflow-shaped fragment
- returned `Workflow`

That validation must check, when possible:

- graph integrity of the materialized structure
- internal references inside the returned structure
- compatibility of any direct references from the returned structure into the existing static graph
- correct use of `then` when the returned structure relies on it as a continuation anchor

The validator must not require every returned fragment to use `then`.

A returned fragment is valid if it already routes correctly into the existing graph, or if `then` supplies the required continuation anchor.

### Join Contracts

The validator must verify:

- that `Join()` is only used as the reserved `result` node
- that all statically-known contributors to `result` are compatible with each other when required
- that `Join(run=reducer)` receives a reducer whose input type is compatible with the collected contribution type
- that the reducer return type becomes the workflow result type

If `Join()` is used without a reducer, the workflow result type is inferred as `list[T]`, where `T` is the contribution type when that type is known.

## 3. Semi-Static Runtime Validation

Semi-static runtime validation covers graph structure and packet shapes that are not fully knowable at definition time.

This is required for:

- `yield`-based fan-out
- dynamic workflow expansion
- self-writing workflows
- static workflows with allowed cycles
- runtime materialization of child workflows
- join contributions that are not fully knowable statically

The runtime validator must verify:

- that yielded packets are compatible with the downstream receiving contract
- that dynamically materialized workflows still satisfy graph integrity rules
- that dynamically materialized nodes and fragments satisfy graph integrity rules in their current materialized form
- that allowed cycles remain within the active cycle budgets
- that runtime branch contributions to `Join` are compatible with the join reducer
- that runtime child workflow boundaries still satisfy the parent contract

If a returned node or fragment itself contains `Expand(...)`, Elan must validate:

- the current materialized graph immediately
- the nested dynamic continuation later, when that nested expansion materializes

Semi-static runtime validation must validate the known current graph, not speculative future expansions.

Semi-static runtime validation fails clearly and at the narrowest possible boundary.

## Strongly Typed And Weakly Typed Tasks

Elan must support both:

- strongly typed tasks
- weakly typed tasks

### Strongly Typed Tasks

Strongly typed tasks have:

- parameter annotations
- return annotations
- structured payloads declared through registered ref classes when needed

These tasks receive the strongest static validation.

### Weakly Typed Tasks

Weakly typed tasks may:

- omit annotations
- use `Any`
- expose only partial type information

These tasks must remain valid Elan tasks.

However, missing type information must reduce the strength of validation rather than silently pretending stronger guarantees exist.

That means:

- static validation degrades when information is missing
- runtime validation remains active at the workflow boundaries Elan can still observe

## Inference Requirements

Elan must infer node-facing contracts from:

- task signatures
- task return annotations
- `Node.bind_output`
- child workflow `result`
- `Join(...)`

### Output Adaptation Inference

`Node.bind_output` is part of the type contract, not just a runtime convenience.

Examples:

- `bind_output="name"` turns a scalar into a named packet with one field
- `bind_output=["name", "style"]` turns a tuple into a named packet with two fields

The validator must reason over that exposed packet shape even if Elan does not surface it as a public Python class.

### Workflow Result Inference

Each workflow must have a derived result contract:

- if `result` is a plain node, use that node's exposed type
- if `result` is a `Join`, use the join output type

That derived result type is what parent workflows see when they run the workflow in a node.

## Error Handling Requirements

Validation failures must be:

- explicit
- local
- actionable

Error reporting identifies:

- the workflow
- the node or graph element involved
- the field or route involved
- the reason validation failed

Validation must not rely on vague fallback behavior when the workflow contract is already invalid.

## Non-Goals

The validation/type system is not required to:

- prove arbitrary Python code correct
- infer the full behavior of task internals
- replace runtime checks entirely
- require full typing for all workflows

The system improves safety and clarity without making Elan unusable for partially typed codebases.

## Summary Of Required Coverage

The validation system must cover:

- graph integrity
- task input/output contracts
- output adaptation
- input adaptation
- context reads and writes
- routing correctness
- dynamic continuation correctness
- join correctness
- sub-workflow boundaries
- runtime-materialized graph segments

That is the minimum scope for Elan's first serious validation system.
