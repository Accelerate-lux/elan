"""Toy application screening workflow using yield-based batch fan-out.

The process is deliberately small:
1. Load fake application rows inside the workflow.
2. Yield one typed application per row.
3. Screen each yielded application on its own branch.
4. Reject applications without tax/contact verification, over the request cap,
   or missing enough budget/problem detail.
5. Stop early on hard-gate failure, or continue into scoring layers.
6. Score priority category fit, pilot/usage traction, delivery owner/timeline,
   and contradiction count.
7. Convert the layer scores into a final bucket.
8. Join all screened applications and aggregate the batch inside the workflow.

The yield and aggregation refactor is now visible, but some remaining limitations
are still deliberate:
- provider-like settings are passed through workflow context
- gates and scoring layers inside one application are still serialized
- concurrency is controlled nowhere in the workflow/runtime contract
"""

import asyncio
from typing import Any, Literal

from pydantic import BaseModel, Field

from elan import Input, Join, Node, Workflow, ref, task


class ToyApplication(BaseModel):
    row_number: int
    applicant_name: str
    tax_id_present: bool
    contact_email_verified: bool
    requested_amount_usd: int
    budget_line_items: int
    problem_statement_words: int
    category: str
    pilot_users: int
    monthly_active_users: int
    delivery_owner_named: bool
    delivery_timeline_weeks: int
    contradiction_count: int = 0


class ToyFinalScores(BaseModel):
    traction_score: int
    category_fit_score: int
    delivery_readiness_score: int
    consistency_score: int
    composite_score: int
    bucket: Literal["A", "B", "C", "D"]
    hard_fail_reasons: list[str] = Field(default_factory=list)


class ToyScreeningContext(BaseModel):
    provider: str = "deterministic"
    model: str = "toy-reviewer"
    temperature: float = 0.0
    stop_on_hard_gate_fail: bool = True
    a_threshold: int = 80
    b_threshold: int = 60
    max_requested_amount_usd: int = 100_000
    min_budget_line_items: int = 4
    min_problem_statement_words: int = 120
    priority_categories: list[str] = Field(
        default_factory=lambda: ["operations", "maintenance", "compliance"]
    )
    min_pilot_users: int = 10
    min_monthly_active_users: int = 250
    max_delivery_timeline_weeks: int = 12


@ref
class ToyReviewState(BaseModel):
    app: ToyApplication
    hard_gate_failures: list[str] = Field(default_factory=list)
    review_route: Literal["continue", "stop"] = "continue"
    category_fit_score: int = 0
    traction_score: int = 0
    delivery_readiness_score: int = 0
    consistency_score: int = 0
    final: ToyFinalScores | None = None


class ToyBatchSummary(BaseModel):
    total: int
    accepted: int
    rejected: int
    average_score: float


def toy_rows() -> list[dict[str, Any]]:
    return [
        {
            "Applicant": "Atlas Inventory Co.",
            "tax_id_present": True,
            "contact_email_verified": True,
            "requested_amount_usd": 75_000,
            "budget_line_items": 8,
            "problem_statement_words": 220,
            "category": "operations",
            "pilot_users": 14,
            "monthly_active_users": 380,
            "delivery_owner_named": True,
            "delivery_timeline_weeks": 10,
            "contradiction_count": 0,
        },
        {
            "Applicant": "Blue Kite Learning",
            "tax_id_present": True,
            "contact_email_verified": True,
            "requested_amount_usd": 62_000,
            "budget_line_items": 5,
            "problem_statement_words": 160,
            "category": "education",
            "pilot_users": 3,
            "monthly_active_users": 40,
            "delivery_owner_named": True,
            "delivery_timeline_weeks": 18,
            "contradiction_count": 0,
        },
        {
            "Applicant": "Crescent Health Desk",
            "tax_id_present": False,
            "contact_email_verified": False,
            "requested_amount_usd": 48_000,
            "budget_line_items": 6,
            "problem_statement_words": 190,
            "category": "compliance",
            "pilot_users": 11,
            "monthly_active_users": 220,
            "delivery_owner_named": True,
            "delivery_timeline_weeks": 9,
            "contradiction_count": 1,
        },
        {
            "Applicant": "Delta Maintenance Lab",
            "tax_id_present": True,
            "contact_email_verified": True,
            "requested_amount_usd": 125_000,
            "budget_line_items": 2,
            "problem_statement_words": 80,
            "category": "maintenance",
            "pilot_users": 0,
            "monthly_active_users": 0,
            "delivery_owner_named": False,
            "delivery_timeline_weeks": 16,
            "contradiction_count": 0,
        },
    ]


def toy_screening_config() -> dict[str, Any]:
    return {
        "provider": "deterministic",
        "model": "toy-reviewer",
        "temperature": 0.0,
        "stop_on_hard_gate_fail": True,
        "a_threshold": 80,
        "b_threshold": 60,
        "max_requested_amount_usd": 100_000,
        "min_budget_line_items": 4,
        "min_problem_statement_words": 120,
        "min_pilot_users": 10,
        "min_monthly_active_users": 250,
        "max_delivery_timeline_weeks": 12,
    }


@task
async def load_applications():
    for row_number, fields in enumerate(toy_rows(), start=2):
        await asyncio.sleep(0)
        yield ToyApplication(
            row_number=row_number,
            applicant_name=fields["Applicant"],
            tax_id_present=fields["tax_id_present"],
            contact_email_verified=fields["contact_email_verified"],
            requested_amount_usd=fields["requested_amount_usd"],
            budget_line_items=fields["budget_line_items"],
            problem_statement_words=fields["problem_statement_words"],
            category=fields["category"],
            pilot_users=fields["pilot_users"],
            monthly_active_users=fields["monthly_active_users"],
            delivery_owner_named=fields["delivery_owner_named"],
            delivery_timeline_weeks=fields["delivery_timeline_weeks"],
            contradiction_count=fields["contradiction_count"],
        )


@task
async def prepare_application(app: ToyApplication) -> ToyReviewState:
    return ToyReviewState(app=app)


@task
async def review_identity_gate(
    state: ToyReviewState,
    screening: ToyScreeningContext,
) -> ToyReviewState:
    _ = screening.provider, screening.model, screening.temperature
    if state.app.tax_id_present and state.app.contact_email_verified:
        return state
    return state.model_copy(
        update={"hard_gate_failures": [*state.hard_gate_failures, "identity"]}
    )


@task
async def review_budget_gate(
    state: ToyReviewState,
    screening: ToyScreeningContext,
) -> ToyReviewState:
    _ = screening.provider, screening.model, screening.temperature
    if state.app.requested_amount_usd <= screening.max_requested_amount_usd:
        return state
    return state.model_copy(
        update={"hard_gate_failures": [*state.hard_gate_failures, "budget"]}
    )


@task
async def review_submission_gate(
    state: ToyReviewState,
    screening: ToyScreeningContext,
) -> ToyReviewState:
    _ = screening.provider, screening.model, screening.temperature
    if (
        state.app.budget_line_items >= screening.min_budget_line_items
        and state.app.problem_statement_words >= screening.min_problem_statement_words
    ):
        return state
    return state.model_copy(
        update={"hard_gate_failures": [*state.hard_gate_failures, "submission"]}
    )


@task
async def decide_review_route(
    state: ToyReviewState,
    screening: ToyScreeningContext,
) -> ToyReviewState:
    route = (
        "stop"
        if screening.stop_on_hard_gate_fail and state.hard_gate_failures
        else "continue"
    )
    return state.model_copy(update={"review_route": route})


@task
async def review_category_fit(
    state: ToyReviewState,
    screening: ToyScreeningContext,
) -> ToyReviewState:
    _ = screening.provider, screening.model, screening.temperature
    score = 25 if state.app.category in screening.priority_categories else 0
    return state.model_copy(update={"category_fit_score": score})


@task
async def review_traction(
    state: ToyReviewState,
    screening: ToyScreeningContext,
) -> ToyReviewState:
    _ = screening.provider, screening.model, screening.temperature
    score = (
        25
        if state.app.pilot_users >= screening.min_pilot_users
        or state.app.monthly_active_users >= screening.min_monthly_active_users
        else 0
    )
    return state.model_copy(update={"traction_score": score})


@task
async def review_delivery_readiness(
    state: ToyReviewState,
    screening: ToyScreeningContext,
) -> ToyReviewState:
    _ = screening.provider, screening.model, screening.temperature
    score = (
        25
        if state.app.delivery_owner_named
        and state.app.delivery_timeline_weeks <= screening.max_delivery_timeline_weeks
        else 0
    )
    return state.model_copy(update={"delivery_readiness_score": score})


@task
async def review_consistency(
    state: ToyReviewState,
    screening: ToyScreeningContext,
) -> ToyReviewState:
    _ = screening.provider, screening.model, screening.temperature
    score = 25 if state.app.contradiction_count == 0 else 0
    return state.model_copy(update={"consistency_score": score})


@task
async def score_application(
    state: ToyReviewState,
    screening: ToyScreeningContext,
) -> ToyReviewState:
    composite = (
        state.category_fit_score
        + state.traction_score
        + state.delivery_readiness_score
        + state.consistency_score
    )
    if state.hard_gate_failures:
        bucket = "D"
    elif composite >= screening.a_threshold:
        bucket = "A"
    elif composite >= screening.b_threshold:
        bucket = "B"
    else:
        bucket = "C"
    return state.model_copy(
        update={
            "final": ToyFinalScores(
                traction_score=state.traction_score,
                category_fit_score=state.category_fit_score,
                delivery_readiness_score=state.delivery_readiness_score,
                consistency_score=state.consistency_score,
                composite_score=composite,
                bucket=bucket,
                hard_fail_reasons=state.hard_gate_failures,
            )
        }
    )


@task
def summarize_batch(states: list[ToyReviewState]) -> ToyBatchSummary:
    accepted = sum(
        1 for state in states if state.final and state.final.bucket in {"A", "B"}
    )
    total = len(states)
    average = (
        sum(state.final.composite_score for state in states if state.final) / total
        if total
        else 0.0
    )
    return ToyBatchSummary(
        total=total,
        accepted=accepted,
        rejected=total - accepted,
        average_score=average,
    )


class ApplicationScreeningWorkflow(Workflow):
    name = "toy_current_application_screening"
    context = ToyScreeningContext
    bind_context = {
        "provider": Input.provider,
        "model": Input.model,
        "temperature": Input.temperature,
        "stop_on_hard_gate_fail": Input.stop_on_hard_gate_fail,
        "a_threshold": Input.a_threshold,
        "b_threshold": Input.b_threshold,
        "max_requested_amount_usd": Input.max_requested_amount_usd,
        "min_budget_line_items": Input.min_budget_line_items,
        "min_problem_statement_words": Input.min_problem_statement_words,
        "min_pilot_users": Input.min_pilot_users,
        "min_monthly_active_users": Input.min_monthly_active_users,
        "max_delivery_timeline_weeks": Input.max_delivery_timeline_weeks,
    }

    start = Node(run=load_applications, next="prepare")
    prepare = Node(run=prepare_application, next="identity")
    identity = Node(run=review_identity_gate, next="budget")
    budget = Node(run=review_budget_gate, next="submission")
    submission = Node(
        run=review_submission_gate,
        next="hard_gate_route",
    )
    hard_gate_route = Node(
        run=decide_review_route,
        route_on=ToyReviewState.review_route,
        next={
            "continue": "category_fit",
            "stop": "score",
        },
    )
    category_fit = Node(run=review_category_fit, next="traction")
    traction = Node(run=review_traction, next="delivery_readiness")
    delivery_readiness = Node(
        run=review_delivery_readiness,
        next="consistency",
    )
    consistency = Node(run=review_consistency, next="score")
    score = Node(run=score_application, next="result")
    result = Join(run=summarize_batch)


toy_current_application_workflow = ApplicationScreeningWorkflow()


async def run_toy_application_screening() -> ToyBatchSummary:
    screening_config = toy_screening_config()
    run = await toy_current_application_workflow.run(**screening_config)
    return run.result


if __name__ == "__main__":
    summary = asyncio.run(run_toy_application_screening())
    print(summary.model_dump_json(indent=2))
