# ruff: noqa: F821, PIE794
"""Toy application screening workflow using yield-based batch fan-out.

The process is deliberately small:
1. Expose a typed Python `run(...)` signature for the workflow's public inputs.
2. Accept screening settings as ordinary user data, not as Elan policy/context.
3. Load fake application rows inside the workflow.
4. Yield one typed review state per row.
5. Screen each yielded state on its own branch.
6. Screen each application through child workflows with internal fan-out/fan-in.
7. Reject applications without tax/contact verification, over the request cap,
   or missing enough budget/problem detail.
8. Stop early on hard-gate failure, or continue into scoring layers.
9. Score priority category fit, pilot/usage traction, delivery owner/timeline,
   and contradiction count.
10. Convert the layer scores into a final bucket.
11. Join all screened applications and aggregate the batch inside the workflow.

The example deliberately keeps the framework/user-data boundaries visible:
- domain configuration is ordinary user data, not Elan context or policy
- provider-like metadata and the active review are held in branch context
- parallel tasks return typed decisions instead of copied review states
- scoped joins merge those decisions into their owning context
- concurrency is governed by Elan workflow policy
- batch fan-out uses generator yields
- successful child workflows commit their context before the parent continues
"""

import asyncio
from typing import Any, Literal

from pydantic import BaseModel, Field

from elan import Binder, Input, Join, Node, Workflow, WorkflowPolicy, ref, task


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


class ToyScreeningConfig(BaseModel):
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
    config: ToyScreeningConfig
    hard_gate_failures: list[str] = Field(default_factory=list)
    review_route: Literal["continue", "stop"] = "continue"
    category_fit_score: int = 0
    traction_score: int = 0
    delivery_readiness_score: int = 0
    consistency_score: int = 0
    final: ToyFinalScores | None = None


GateName = Literal["identity", "budget", "submission"]
ScoreLayerName = Literal[
    "category_fit",
    "traction",
    "delivery_readiness",
    "consistency",
]


class GateDecision(BaseModel):
    gate: GateName
    passed: bool


@ref
class ReviewRoute(BaseModel):
    value: Literal["continue", "stop"]


class LayerScore(BaseModel):
    layer: ScoreLayerName
    score: int


class ScoreSummary(BaseModel):
    category_fit: int
    traction: int
    delivery_readiness: int
    consistency: int


class ToyScreeningContext(BaseModel):
    provider: str = "deterministic"
    model: str = "toy-reviewer"
    temperature: float = 0.0
    review: ToyReviewState | None = None

    def current_review(self) -> ToyReviewState:
        if self.review is None:
            raise RuntimeError("Screening context does not contain an active review.")
        return self.review


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


def toy_screening_settings() -> ToyScreeningConfig:
    return ToyScreeningConfig.model_validate(toy_screening_config())


@task
async def load_applications(config: ToyScreeningConfig):
    for row_number, fields in enumerate(toy_rows(), start=2):
        await asyncio.sleep(0)
        yield ToyReviewState(
            app=ToyApplication(
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
            ),
            config=config,
        )


@task
async def prepare_application(
    state: ToyReviewState,
    screening: ToyScreeningContext,
) -> ToyReviewState:
    screening.review = state
    return state


@task
def begin_review_stage(screening: ToyScreeningContext) -> None:
    screening.current_review()


@task
async def review_identity_gate(
    screening: ToyScreeningContext,
) -> GateDecision:
    _ = screening.provider, screening.model, screening.temperature
    state = screening.current_review()
    return GateDecision(
        gate="identity",
        passed=state.app.tax_id_present and state.app.contact_email_verified,
    )


@task
async def review_budget_gate(
    screening: ToyScreeningContext,
) -> GateDecision:
    _ = screening.provider, screening.model, screening.temperature
    state = screening.current_review()
    return GateDecision(
        gate="budget",
        passed=(
            state.app.requested_amount_usd
            <= state.config.max_requested_amount_usd
        ),
    )


@task
async def review_submission_gate(
    screening: ToyScreeningContext,
) -> GateDecision:
    _ = screening.provider, screening.model, screening.temperature
    state = screening.current_review()
    return GateDecision(
        gate="submission",
        passed=(
            state.app.budget_line_items >= state.config.min_budget_line_items
            and state.app.problem_statement_words
            >= state.config.min_problem_statement_words
        ),
    )


@task
async def review_category_fit(
    screening: ToyScreeningContext,
) -> LayerScore:
    _ = screening.provider, screening.model, screening.temperature
    state = screening.current_review()
    score = 25 if state.app.category in state.config.priority_categories else 0
    return LayerScore(layer="category_fit", score=score)


@task
async def review_traction(
    screening: ToyScreeningContext,
) -> LayerScore:
    _ = screening.provider, screening.model, screening.temperature
    state = screening.current_review()
    score = (
        25
        if state.app.pilot_users >= state.config.min_pilot_users
        or state.app.monthly_active_users >= state.config.min_monthly_active_users
        else 0
    )
    return LayerScore(layer="traction", score=score)


@task
async def review_delivery_readiness(
    screening: ToyScreeningContext,
) -> LayerScore:
    _ = screening.provider, screening.model, screening.temperature
    state = screening.current_review()
    score = (
        25
        if state.app.delivery_owner_named
        and state.app.delivery_timeline_weeks
        <= state.config.max_delivery_timeline_weeks
        else 0
    )
    return LayerScore(layer="delivery_readiness", score=score)


@task
async def review_consistency(
    screening: ToyScreeningContext,
) -> LayerScore:
    _ = screening.provider, screening.model, screening.temperature
    state = screening.current_review()
    score = 25 if state.app.contradiction_count == 0 else 0
    return LayerScore(layer="consistency", score=score)


@task
async def score_application(
    screening: ToyScreeningContext,
) -> ToyReviewState:
    state = screening.current_review()
    composite = (
        state.category_fit_score
        + state.traction_score
        + state.delivery_readiness_score
        + state.consistency_score
    )
    if state.hard_gate_failures:
        bucket = "D"
    elif composite >= state.config.a_threshold:
        bucket = "A"
    elif composite >= state.config.b_threshold:
        bucket = "B"
    else:
        bucket = "C"
    state.final = ToyFinalScores(
        traction_score=state.traction_score,
        category_fit_score=state.category_fit_score,
        delivery_readiness_score=state.delivery_readiness_score,
        consistency_score=state.consistency_score,
        composite_score=composite,
        bucket=bucket,
        hard_fail_reasons=state.hard_gate_failures,
    )
    return state


@task
def merge_hard_gate_results(
    decisions: list[GateDecision],
    screening: ToyScreeningContext,
) -> ReviewRoute:
    state = screening.current_review()
    failed = {decision.gate for decision in decisions if not decision.passed}
    state.hard_gate_failures = [
        gate for gate in ("identity", "budget", "submission") if gate in failed
    ]
    state.review_route = (
        "stop"
        if state.config.stop_on_hard_gate_fail and state.hard_gate_failures
        else "continue"
    )
    return ReviewRoute(value=state.review_route)


@task
def merge_score_layer_results(
    layer_scores: list[LayerScore],
    screening: ToyScreeningContext,
) -> ScoreSummary:
    state = screening.current_review()
    scores = {result.layer: result.score for result in layer_scores}
    summary = ScoreSummary(
        category_fit=scores["category_fit"],
        traction=scores["traction"],
        delivery_readiness=scores["delivery_readiness"],
        consistency=scores["consistency"],
    )
    state.category_fit_score = summary.category_fit
    state.traction_score = summary.traction
    state.delivery_readiness_score = summary.delivery_readiness
    state.consistency_score = summary.consistency
    return summary


@task
def finish_application(state: ToyReviewState) -> ToyReviewState:
    return state


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


class HardGateWorkflow(Workflow):
    identity: Node
    budget: Node
    submission: Node
    result: Join

    context = ToyScreeningContext

    start = Node(
        run=begin_review_stage,
        next=[
            identity,
            budget,
            submission,
        ],
    )
    identity = Node(run=review_identity_gate, next=result)
    budget = Node(run=review_budget_gate, next=result)
    submission = Node(run=review_submission_gate, next=result)
    result = Join(run=merge_hard_gate_results, scope=start)


class ScoringLayersWorkflow(Workflow):
    category_fit: Node
    traction: Node
    delivery_readiness: Node
    consistency: Node
    result: Join

    context = ToyScreeningContext

    start = Node(
        run=begin_review_stage,
        next=[category_fit, traction, delivery_readiness, consistency],
    )
    category_fit = Node(run=review_category_fit, next=result)
    traction = Node(run=review_traction, next=result)
    delivery_readiness = Node(run=review_delivery_readiness, next=result)
    consistency = Node(run=review_consistency, next=result)
    result = Join(run=merge_score_layer_results, scope=start)


class ScreenApplicationWorkflow(Workflow):
    hard_gates: Node
    scoring_layers: Node
    score: Node
    result: Node

    context = ToyScreeningContext

    start = Node(run=prepare_application, next=hard_gates)
    hard_gates = Node(
        run=HardGateWorkflow(),
        route_on=ReviewRoute.value,
        next={
            "continue": scoring_layers,
            "stop": score,
        },
    )
    scoring_layers = Node(run=ScoringLayersWorkflow(), next=score)
    score = Node(run=score_application, next=result)
    result = Node(run=finish_application)


class ApplicationScreeningWorkflow(Workflow):
    screen_application: Node
    result: Join

    name = "toy_current_application_screening"
    policy = WorkflowPolicy(max_parallel_tasks=4)
    context = ToyScreeningContext
    bind_context = Binder[ToyScreeningContext](
        provider=Input.provider,
        model=Input.model,
        temperature=Input.temperature,
    )

    start = Node(
        run=load_applications,
        bind_input=Binder[load_applications](config=Input.config),
        next=screen_application,
    )
    screen_application = Node(run=ScreenApplicationWorkflow(), next=result)
    result = Join(run=summarize_batch)

    async def run(
        self,
        *,
        provider: str = "deterministic",
        model: str = "toy-reviewer",
        temperature: float = 0.0,
        config: ToyScreeningConfig,
    ):
        return await self._run(
            provider=provider,
            model=model,
            temperature=temperature,
            config=config,
        )


toy_current_application_workflow = ApplicationScreeningWorkflow()


async def run_toy_application_screening() -> ToyBatchSummary:
    screening_config = toy_screening_config()
    run = await toy_current_application_workflow.run(
        provider=screening_config["provider"],
        model=screening_config["model"],
        temperature=screening_config["temperature"],
        config=toy_screening_settings(),
    )
    return run.result


if __name__ == "__main__":
    summary = asyncio.run(run_toy_application_screening())
    print(summary.model_dump_json(indent=2))
