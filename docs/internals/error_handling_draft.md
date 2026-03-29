# Error Handling Draft

This note collects draft ideas for Elan error semantics.

It is not part of the locked interface design yet.

The goal is to keep candidate categories and behaviors visible without hardening them too early.

## Scope

This draft covers:

- error categories
- detection point
- failure scope
- possible handling behavior

It does not define the final runtime or API error model.

## Draft Error Categories

### Definition Errors

Examples:

- invalid static graph
- invalid static type contract
- forbidden `Join` placement
- forbidden `Expand(...)` usage
- cycles present while workflow policy forbids them

Current direction:

- detected before execution
- workflow is invalid
- no run starts

### Run Start Validation Errors

Examples:

- invalid top-level input payload
- invalid config or API workflow payload
- missing required registered refs

Current direction:

- detected before execution starts
- run is rejected

### Task Execution Errors

Examples:

- task raises
- task input adaptation fails
- output adaptation fails

Open questions:

- whether the default failure scope is the branch, workflow, or whole run
- whether retries belong in the core policy model

### Context Update Errors

Examples:

- unknown field write
- incompatible value written to a context field
- invalid `after.context` update

Current direction:

- statically provable errors fail definition-time validation
- runtime-only errors fail when the update is attempted

Open questions:

- whether context writes are always atomic
- whether policy may downgrade some context update failures

### Dynamic Expansion Errors

Examples:

- malformed returned `Node`
- malformed returned fragment
- invalid returned `Workflow`
- returned structure references missing nodes
- returned structure violates current graph rules

Current direction:

- detected when the expansion result is materialized
- invalid returned structure is rejected before append

Open questions:

- whether the default failure scope is the branch, workflow, or run
- whether some policy modes may skip the expansion and continue

### Policy Violations

Examples:

- graph budget exceeded
- time budget exceeded
- feature disabled by policy
- cycle step attempted while cycles are disabled

This category is closely tied to policy design.

Open questions:

- which violations fail the branch
- which violations fail the workflow
- which violations fail the whole run
- whether handling is fully configurable per violation class

### Join Errors

Examples:

- invalid runtime join contribution
- reducer failure
- forbidden heterogeneous contribution set

Open questions:

- whether join errors always fail the owning workflow
- whether policy can change join failure scope

### Cancellation

Examples:

- explicit user cancellation
- cancellation propagated from a parent scope

Current direction:

- cancellation stays distinct from failure

Open questions:

- exact cancellation cascade semantics
- visible run status and child status behavior

### Internal Engine Errors

Examples:

- scheduler invariant broken
- impossible routing state
- corrupted execution state

Current direction:

- treated separately from user workflow errors

Open questions:

- whether they always fail the whole run
- how much internal detail is exposed through API responses

## Draft Handling Behaviors

Candidate handling behaviors:

- reject before run
- reject before append
- fail current branch
- fail current workflow
- fail current sub-workflow
- fail whole run
- cancel current scope
- cancel whole run

These are candidate behaviors only.

The final design still needs:

- a mapping from error category to default handling behavior
- a statement of which behaviors are configurable
- a statement of which behaviors are hard rules

## Open Review Points

- the final error taxonomy
- propagation rules across branch, workflow, sub-workflow, and run scopes
- atomicity rules for context updates and dynamic appends
- the relationship between policy violations and ordinary runtime failures
- error reporting shape in Python, config, and API responses
