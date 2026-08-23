# Prefect

_Reviewed against primary documentation in August 2026._

Prefect is the Python-first and operational-maturity baseline in this comparison
set. See the [shared scenario](baseline_workflow.md) and
[dynamic taxonomy](dynamic_models.md).

## What Prefect is best at

Prefect is strongest when a team wants orchestration to feel like ordinary
Python while retaining task states, retries, caching, timeouts, concurrency,
deployments, schedules, workers, and remote interaction. Flows and tasks are
decorated callables; tasks may be called synchronously, submitted to a task
runner, mapped, or delayed to task workers.

## Capabilities assessment

Prefect's dynamic behavior primarily comes from imperative Python control flow
inside flows. A flow can use ordinary conditions and loops, call tasks, and
compose nested flows. This is flexible, but it does not make run-specific graph
materialization a distinct authoring boundary.

Composition and workload breadth are strong. Deployments expose flows for
scheduled, event-triggered, or on-demand execution, and task runners cover
thread, process, and external distributed execution models.

## AI-era developer experience

AI makes Prefect's compact syntax easier to produce and gives authoring agents a
large documentation and example corpus. Prefect publishes an `llms.txt` index
and dedicated AI guidance. These are material adoption advantages alongside its
operational maturity.

Elan's narrower advantage is review structure. Routes, joins, bindings, and the
Experimental `Expand` boundary live in declarations instead of arbitrary flow
control. That can make AI-written topology easier to audit, but two complementary
review features—direct invocation of registered tasks and declaration-only graph
inspection—remain **Planned** in Elan.

| Experience | Prefect | Elan today |
| --- | --- | --- |
| Initial authoring | Compact ordinary Python | Small explicit graph vocabulary |
| Dynamic decisions | Primarily Python control flow | Declared routes plus Experimental fragments |
| Decorated task calls | Direct instrumented calls, submit, map, delay | Direct registered-task calls are **Planned** |
| Operations | Deployments, workers, retries, states, schedules | **Direction** |
| AI documentation | Broad docs and `llms.txt` | Focused product docs and `llms.txt` |

## Where Prefect fits well

Choose Prefect when operational maturity, integrations, deployment flexibility,
and familiar imperative Python matter more than making graph topology a separate
review artifact.

## Where Elan differs

Elan is not a lighter replacement for Prefect's platform. Its differentiation
is a workload-neutral, declaration-oriented graph model and a typed boundary for
Experimental runtime graph growth. Teams should accept Elan's missing durability
and operations surface before evaluating that programming-model advantage.

## References

- [Prefect concepts](https://docs.prefect.io/v3/concepts)
- [Prefect flows](https://docs.prefect.io/v3/concepts/flows)
- [Prefect tasks](https://docs.prefect.io/v3/concepts/tasks)
- [Prefect task runners](https://docs.prefect.io/v3/concepts/task-runners)
- [Prefect deployments](https://docs.prefect.io/v3/how-to-guides/deployments/create-deployments)
- [Prefect AI guidance](https://docs.prefect.io/v3/how-to-guides/ai)
