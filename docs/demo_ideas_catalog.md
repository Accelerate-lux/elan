# Demo Ideas Catalog

This note is a lightweight catalog of possible Elan demos.

It is intentionally a planning surface, not a roadmap or a final decision document.

The goal is to keep promising ideas in one place so they can be revisited, compared, and shaped into fuller demos later.

## What makes a strong demo

- Should support simple examples first
- Should naturally justify dynamic graph expansion
- Should allow nested subworkflows and branch / barrier semantics
- Should support mixed deterministic tasks and agent steps
- Should be vivid and memorable, not just a boring CRUD or ETL example

## Candidate Demo Directions

### Email processing

A simple mail-processing workflow is a strong demo direction.

Why it fits:

- It is easy to understand quickly
- It has a clear business flavor without needing a large domain setup
- It can start as a small linear workflow and later grow into richer routing patterns
- It naturally mixes deterministic parsing with AI classification or drafting

Possible shape:

- First task yields or fetches an email
- Parse subject, sender, body, and metadata
- Classify intent or urgency
- Extract structured information
- Produce a recommended action, draft reply, or routing decision

Possible variants:

- Inbox triage
- Support email intake
- Sales lead qualification
- Escalation and response drafting

### AI-in-the-loop ETL recovery

A simple ETL workflow with an AI-assisted error handling loop is another strong demo direction.

Why it fits:

- It shows deterministic processing and agentic recovery in the same workflow
- It gives a concrete reason for retries, loops, and explicit error handling
- It feels operational rather than gimmicky
- It highlights the value of orchestration instead of using AI as a decorative extra

Possible shape:

- Ingest source data
- Normalize and validate it
- Run a transform step
- If the step fails, route the error context to an AI repair or diagnosis step
- Apply the suggested fix or adjusted transform
- Retry the failed step
- Escalate or stop after a bounded number of attempts

Possible variants:

- CSV cleanup and schema repair
- Log ingestion with malformed records
- Data enrichment with partial failures
- Mapping legacy records into a stricter target model

### Saga pattern / trip booking

A saga-pattern demo modeled after a trip-booking flow is another strong candidate.

Why it fits:

- It is a classic orchestration problem rather than a toy example
- It shows explicit multi-step coordination across several services
- It gives a natural role to compensating actions and rollback
- It highlights the difference between a plain retry and a true business-level recovery flow

Possible shape:

- Start a trip-booking request
- Reserve a flight
- Reserve a hotel
- Reserve a car
- If a later step fails, trigger compensating actions for the earlier successful steps
- Run compensations in reverse order and return a structured failure result

Core behaviors worth demonstrating:

- Sequential business transactions
- Per-step compensation handlers
- Reverse-order rollback
- Bounded retries for transient failures
- Non-retryable failures that trigger compensation immediately

Possible variants:

- Vacation booking
- Order placement with payment, inventory, and shipping reservation
- Employee onboarding with account, device, and access provisioning
- Subscription signup with billing, entitlement, and notification setup

### Client onboarding loop

A client-onboarding workflow is a strong business-process demo with room for review loops and escalation.

Why it fits:

- It is easy to map to a real business process
- It naturally combines deterministic validation, document checks, and human or AI review
- It gives a clear reason for iterative correction loops before completion
- It can scale from a simple happy path to a richer orchestration story

Possible shape:

- Receive a client onboarding request
- Validate identity, company details, and required documents
- If information is missing or inconsistent, request clarification or correction
- Re-run validation after new material arrives
- Provision accounts, permissions, or downstream services after approval

Possible variants:

- KYC onboarding
- Enterprise account setup
- Vendor onboarding
- Partner registration

### Research agent

A research-agent workflow is a strong fit for demos centered on iterative expansion and synthesis.

Why it fits:

- It makes dynamic graph growth feel natural rather than forced
- It combines planning, retrieval, synthesis, and verification cleanly
- It gives a clear reason for sub-questions, recursion, and review loops
- It is legible to both technical and non-technical audiences

Possible shape:

- Start from a user question
- Expand into sub-questions or investigation threads
- Gather sources or evidence
- Synthesize findings into a draft answer or brief
- Run a verification or critique pass
- Refine the result if confidence is low

Possible variants:

- Market landscape brief
- Technical research assistant
- Competitive analysis
- Literature review assistant

### Software QA and bug resolution

A software-QA workflow is a strong demo for engineering-facing orchestration.

Why it fits:

- It is directly relevant to developer workflows
- It combines deterministic checks with agentic diagnosis and repair suggestions
- It gives a concrete reason for retries, triage, and bounded fix loops
- It can show both automation and human escalation paths

Possible shape:

- Run a targeted test suite or validation plan
- Collect failures, logs, and context
- Classify the issue type
- Ask an AI step to diagnose the likely cause or propose a patch
- Re-run the failing checks
- Escalate unresolved issues or open a structured bug report

Possible variants:

- Failing test triage
- Release readiness gate
- Regression investigation
- Bug reproduction and fix suggestion

### Incident response

An incident-response workflow is a strong operations demo.

Why it fits:

- It gives a natural reason for fan-out, enrichment, and synthesis
- It feels high-stakes and operational without being domain-specific
- It combines automated investigation with recommendation and escalation
- It can illustrate loops, branching, and convergence clearly

Possible shape:

- Ingest an alert or incident trigger
- Gather related logs, metrics, traces, or recent changes
- Branch into several investigation paths
- Summarize likely causes and recommended actions
- Open remediation steps or escalate to a human responder

Possible variants:

- Site reliability incident triage
- Security alert investigation
- Data pipeline incident response
- Customer-facing outage diagnosis

### Lead qualification and follow-up

A lead-qualification workflow is a clean business demo with clear enrichment and routing steps.

Why it fits:

- It is easy to understand and explain
- It naturally combines external enrichment, scoring, and drafting
- It supports clear routing outcomes based on quality or intent
- It can mix deterministic scoring with AI summarization or outreach generation

Possible shape:

- Ingest a new inbound lead
- Enrich with company and contact data
- Score fit and urgency
- Draft follow-up messaging or next actions
- Route high-value leads for manual review and the rest into automated follow-up

Possible variants:

- Sales lead triage
- Partnership pipeline qualification
- Recruiting candidate sourcing follow-up
- Event signup qualification

### Related demo directions in the same family

#### Support ticket intake

- Similar to email processing, but with less message-format complexity
- Good for extraction, classification, prioritization, and assignment

#### Incident investigation

- Ingest an alert or event
- Gather related logs, metrics, or context
- Use AI to summarize findings and suggest the next step
- Strong fit for branching, enrichment, and synthesis

#### Research brief assembly

- Gather a seed topic or question
- Expand into sub-questions
- Collect and rank findings
- Synthesize a final brief
- Strong fit for multi-step planning and structured outputs

## Notes For Later Planning

### Space / NASA theme

Space remains a strong demo theme for Elan.

Why it fits:

- It is vivid and easy to remember
- It supports both small and large workflow shapes
- It gives natural reasons for fan-out, enrichment, ranking, and synthesis
- It can scale from simple API examples to more dynamic orchestration stories

#### APOD

- Good for the smallest hello-world demos
- Simple API-driven examples
- Useful for single-task and linear workflow examples

#### NeoWs

- Good for dynamic fan-out demos
- Possible use case: fetch near-earth objects in a date range, spawn one branch per object, enrich and summarize results

#### Exoplanet Archive

- Good for structured data workflows
- Possible use case: query candidate systems, fan out by system or planet, enrich data, rank targets, synthesize a mission brief

#### DONKI

- Better fit for event / incident orchestration than exploration
- Possible use case: ingest space weather events, fan out per event, fetch related events, extend investigations dynamically, join findings into an operations summary

## Current Front-Runners

- Email processing and inbox triage
- AI-in-the-loop ETL recovery
- Saga-pattern trip booking
- Client onboarding loop
- Research agent
- Software QA and bug resolution
- Incident response
- Lead qualification and follow-up
- Exoplanet mission planning
- Near-earth object monitoring
- Space weather / mission operations
