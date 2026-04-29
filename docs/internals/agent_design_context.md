# Agent Design Context

This note is not a specification and not a roadmap.
It captures the direction, design philosophy, and working method that emerged through the design dialogue around Elan.

Use it as context when extending the design, reviewing proposals, or continuing internal discussions.

## What Elan Is Becoming

Elan is being shaped as a workflow engine that starts simple in-process but is meant to grow into a production runtime for:

- data workflows
- agent workflows
- mixed systems combining data processing, orchestration, and decision steps

The target is not only a graph authoring DSL and not only a task queue wrapper.
The target is a workflow-first runtime with a clear semantic center.

That center is:

- Elan owns workflow semantics
- Elan owns routing, joins, branch progression, context, and result semantics
- Elan owns scheduling intent and activation lifecycle
- external systems may execute work or store values, but should not define Elan's model

## Core Design Principles

### Explicit Structure

Elan should make graph structure, routing boundaries, result boundaries, and task relationships explicit.
Behavior should not depend on opaque runtime magic when it can be represented clearly in the workflow model.

### Plain Python Tasks

Task code should stay ordinary Python business logic.
Tasks should remain reusable and as independent as possible from orchestration concerns.
The workflow layer should carry orchestration semantics, not the task body.

### Runtime Concerns Stay Out Of Business Logic

Retries, deployment placement, scheduling, routing, context propagation, durability, and execution transport should not leak into task code unless explicitly intended.

### Thin First Slices

Start with the smallest coherent runtime model.
Statuses, persistence, execution contracts, and other runtime surfaces should begin thin and grow only when a real requirement appears.

### Semantic Ownership Before Backend Choice

Before choosing infrastructure or implementation details, first decide what Elan must own semantically and what can be delegated.

Examples:

- Elan owns workflow progression
- workers execute activations, not workflows
- value stores hold large results, but Elan decides when values matter semantically

### Familiar Where Useful, Independent Where Necessary

Elan can stay close to adjacent tools when that helps usability and implementation speed.
Examples include task registration and worker mental models inspired by Taskiq or Celery.

But those tools should remain implementation influences, not the public semantic center of Elan.

## Design Method

The working method is dialogue-based and requirements-driven.
It is not implementation-first and not roadmap-first.

The preferred sequence is:

1. Identify one concrete capability pressure.
2. Clarify what semantic responsibility belongs to Elan.
3. Separate current decisions from open topics.
4. Phrase decisions as durable rules or invariants.
5. Keep the first model thin.
6. Leave replaceable implementation details open when possible.

This means design should not jump directly to architecture because a familiar tool exists.
It should first define what must remain true regardless of backend.

## How To Evaluate A Proposal

When refining Elan, test proposals against these questions:

- Does this keep workflows centered on explicit graph structure and result boundaries?
- Does this keep tasks plain Python and reusable?
- Does this keep orchestration semantics in Elan rather than in task code or infrastructure?
- Does this preserve a simple local path?
- Can the same workflow grow from local execution to production without a rewrite?
- Is the proposal driven by a real requirement or use case, rather than generic platform design?
- Is the model thinner than it could be while still solving the problem correctly?

If a proposal fails several of these checks, it is probably specifying too early or in the wrong layer.

## Design Style To Preserve

Good design notes for Elan should:

- separate settled decisions from open questions
- state what Elan owns semantically
- keep first implementations thin
- distinguish control-plane concerns from data-plane concerns
- avoid overfitting to one backend or one adjacent tool
- stay grounded in practical workflow use cases

Design notes should avoid:

- treating implementation convenience as semantic truth
- over-specifying future systems without requirements pressure
- copying another orchestrator's abstractions by default
- pushing orchestration complexity into task bodies

## Current Direction In One Paragraph

Elan is converging toward a workflow runtime where orchestration semantics stay fully inside Elan, while execution and storage sit behind clear contracts.
The design process favors explicitness, thin first slices, backend replaceability, and requirements-driven refinement.
The goal is to borrow familiar mental models where helpful without letting external tools define Elan's architecture.
