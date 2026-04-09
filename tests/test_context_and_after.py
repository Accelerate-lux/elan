import pytest
from pydantic import BaseModel

from elan import Context, Input, Join, Node, Upstream, Workflow, ref


class RunContext(BaseModel):
    locale: str = "en"
    punctuation: str = "!"
    prefix: str = "draft"
    label: str | None = None
    published_url: str | None = None


@ref
class PublishPayload(BaseModel):
    slug: str
    url: str


@ref
class ContextRoutePayload(BaseModel):
    name: str


@pytest.mark.asyncio
async def test_node_context_writes_literals_before_task_runs(mock_task_factory):
    async def _greet(punctuation: str):
        return punctuation

    greet = mock_task_factory(_greet)

    run = await Workflow(
        "greet",
        context=RunContext,
        start=Node(
            run=greet,
            context={"punctuation": "?"},
            bind_input={"punctuation": Context.punctuation},
        ),
    ).run()

    greet.mock.assert_called_once_with(punctuation="?")
    assert run.result == "?"


@pytest.mark.asyncio
async def test_task_can_receive_whole_context_by_annotation(mock_task_factory):
    async def _show(ctx: RunContext):
        return ctx.locale

    show = mock_task_factory(_show)

    run = await Workflow(
        "show_context",
        context=RunContext,
        start=Node(
            run=show,
            context={"locale": "fr"},
        ),
    ).run()

    show.mock.assert_called_once()
    assert show.mock.call_args.kwargs["ctx"] == RunContext(locale="fr")
    assert run.result == "fr"


@pytest.mark.asyncio
async def test_explicit_binding_overrides_whole_context_injection(mock_task_factory):
    async def _show(ctx: RunContext):
        return ctx.locale

    show = mock_task_factory(_show)

    run = await Workflow(
        "show_context",
        context=RunContext,
        start=Node(
            run=show,
            bind_input={"ctx": {"locale": "de"}},
        ),
    ).run()

    show.mock.assert_called_once()
    assert show.mock.call_args.kwargs["ctx"] == RunContext(locale="de")
    assert run.result == "de"


@pytest.mark.asyncio
async def test_node_context_reads_from_input(mock_task_factory):
    async def _format_label(label: str):
        return label

    format_label = mock_task_factory(_format_label)

    run = await Workflow(
        "format_label",
        context=RunContext,
        start=Node(
            run=format_label,
            context={"label": Input.label},
            bind_input={"label": Context.label},
        ),
    ).run(label="urgent")

    format_label.mock.assert_called_once_with(label="urgent")
    assert run.result == "urgent"


@pytest.mark.asyncio
async def test_node_context_reads_from_existing_context(mock_task_factory):
    async def _show_label(label: str):
        return label

    show_label = mock_task_factory(_show_label)

    run = await Workflow(
        "show_label",
        context=RunContext,
        start=Node(
            run=show_label,
            context={"label": Context.locale},
            bind_input={"label": Context.label},
        ),
    ).run()

    show_label.mock.assert_called_once_with(label="en")
    assert run.result == "en"


@pytest.mark.asyncio
async def test_node_context_reads_from_upstream_for_non_entry_node(mock_task_factory):
    def _prepare():
        return "world"

    async def _greet(label: str):
        return label

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    run = await Workflow(
        "greet_world",
        context=RunContext,
        start=Node(run=prepare, bind_output="name", next="greet"),
        greet=Node(
            run=greet,
            context={"label": Upstream.name},
            bind_input={"label": Context.label},
        ),
    ).run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with(label="world")
    assert run.result == "world"


@pytest.mark.asyncio
async def test_node_context_reads_from_bound_upstream_value(mock_task_factory):
    def _publish() -> tuple[str, str]:
        return "ignored", "https://example.com/post"

    async def _notify(url: str):
        return url

    publish = mock_task_factory(_publish)
    notify = mock_task_factory(_notify)

    run = await Workflow(
        "publish",
        context=RunContext,
        start=Node(
            run=publish,
            bind_output=[..., "url"],
            next="notify",
        ),
        notify=Node(
            context={"published_url": Upstream.url},
            run=notify,
            bind_input={"url": Context.published_url},
        ),
    ).run()

    publish.mock.assert_called_once_with()
    notify.mock.assert_called_once_with(url="https://example.com/post")
    assert run.result == "https://example.com/post"


@pytest.mark.asyncio
async def test_context_updates_partially_merge(mock_task_factory):
    async def _show(prefix: str, punctuation: str):
        return f"{prefix}{punctuation}"

    show = mock_task_factory(_show)

    run = await Workflow(
        "show",
        context=RunContext,
        start=Node(
            run=show,
            context={"prefix": "published"},
            bind_input={
                "prefix": Context.prefix,
                "punctuation": Context.punctuation,
            },
        ),
    ).run()

    show.mock.assert_called_once_with(prefix="published", punctuation="!")
    assert run.result == "published!"


@pytest.mark.asyncio
async def test_unknown_context_key_fails_clearly(mock_task_factory):
    async def _show(label: str):
        return label

    show = mock_task_factory(_show)

    workflow = Workflow(
        "show",
        context=RunContext,
        start=Node(
            run=show,
            context={"missing": "value"},
            bind_input={"label": "unused"},
        ),
    )

    with pytest.raises(TypeError, match="does not define fields: missing"):
        await workflow.run()


@pytest.mark.asyncio
async def test_node_context_without_workflow_context_fails(mock_task_factory):
    async def _show():
        return "ok"

    show = mock_task_factory(_show)

    workflow = Workflow(
        "show",
        start=Node(run=show, context={"label": "value"}),
    )

    with pytest.raises(TypeError, match="cannot use Node.context without workflow context"):
        await workflow.run()


@pytest.mark.asyncio
async def test_invalid_bare_model_field_ref_fails_clearly(mock_task_factory):
    async def _show():
        return "ok"

    show = mock_task_factory(_show)

    workflow = Workflow(
        "show",
        context=RunContext,
        start=Node(run=show, context={"label": ContextRoutePayload.name}),
    )

    with pytest.raises(TypeError, match="cannot use bare model field reference 'ContextRoutePayload.name'"):
        await workflow.run()


@pytest.mark.asyncio
async def test_multiple_whole_context_parameters_fail_clearly(mock_task_factory):
    async def _show(left: RunContext, right: RunContext):
        return left.locale, right.locale

    show = mock_task_factory(_show)

    workflow = Workflow(
        "show_context",
        context=RunContext,
        start=Node(run=show),
    )

    with pytest.raises(
        TypeError,
        match="defines multiple parameters annotated with workflow context model 'RunContext'",
    ):
        await workflow.run()


@pytest.mark.asyncio
async def test_model_passthrough_stays_unchanged(mock_task_factory):
    def _prepare() -> PublishPayload:
        return PublishPayload(slug="hello", url="https://example.com/hello")

    async def _consume(payload: PublishPayload):
        return payload.url

    prepare = mock_task_factory(_prepare)
    consume = mock_task_factory(_consume)

    run = await Workflow(
        "consume_payload",
        context=RunContext,
        start=Node(run=prepare, next="consume"),
        consume=Node(
            run=consume,
            context={"label": "still-works"},
        ),
    ).run()

    prepare.mock.assert_called_once_with()
    consume.mock.assert_called_once()
    assert consume.mock.call_args.args[0] == PublishPayload(
        slug="hello",
        url="https://example.com/hello",
    )
    assert run.result == "https://example.com/hello"


@pytest.mark.asyncio
async def test_branch_local_context_is_isolated_between_siblings(mock_task_factory, branch_id):
    def _prepare():
        return "world"

    async def _email(prefix: str):
        return prefix

    async def _ticket(prefix: str):
        return prefix

    async def _report(prefix: str):
        return prefix

    prepare = mock_task_factory(_prepare)
    email = mock_task_factory(_email)
    ticket = mock_task_factory(_ticket)
    report = mock_task_factory(_report)

    run = await Workflow(
        "branch_contexts",
        context=RunContext,
        start=Node(
            run=prepare,
            context={"prefix": "shared"},
            next=["email", "ticket"],
        ),
        email=Node(
            run=email,
            bind_input={"prefix": Context.prefix},
            next="report_email",
        ),
        ticket=Node(
            run=ticket,
            bind_input={"prefix": Context.prefix},
            next="report_ticket",
        ),
        report_email=Node(
            run=report,
            context={"prefix": "email"},
            bind_input={"prefix": Context.prefix},
        ),
        report_ticket=Node(
            run=report,
            context={"prefix": "ticket"},
            bind_input={"prefix": Context.prefix},
        ),
    ).run()

    prepare.mock.assert_called_once_with()
    email.mock.assert_called_once_with(prefix="shared")
    ticket.mock.assert_called_once_with(prefix="shared")
    assert {call.kwargs["prefix"] for call in report.mock.call_args_list} == {
        "email",
        "ticket",
    }
    assert run.result is None
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": ["world"],
        },
        branch_id[1]: {
            "_email": ["shared"],
            "_report": ["email"],
        },
        branch_id[2]: {
            "_ticket": ["shared"],
            "_report": ["ticket"],
        },
    }


@pytest.mark.asyncio
async def test_join_does_not_merge_sibling_contexts(mock_task_factory):
    async def _prepare(label: str):
        return label

    async def _email(label: str):
        return label

    async def _ticket(label: str):
        return label

    def _collect(values: list[str]):
        return values

    prepare = mock_task_factory(_prepare)
    email = mock_task_factory(_email)
    ticket = mock_task_factory(_ticket)
    collect = mock_task_factory(_collect)

    run = await Workflow(
        "join_contexts",
        context=RunContext,
        start=Node(
            run=prepare,
            context={"label": "shared"},
            bind_input={"label": Context.label},
            next=["email_branch", "ticket_branch"],
        ),
        email_branch=Node(
            run=email,
            context={"label": "email"},
            bind_input={"label": Context.label},
            next="result",
        ),
        ticket_branch=Node(
            run=ticket,
            context={"label": "ticket"},
            bind_input={"label": Context.label},
            next="result",
        ),
        result=Join(run=collect),
    ).run()

    prepare.mock.assert_called_once_with(label="shared")
    email.mock.assert_called_once_with(label="email")
    ticket.mock.assert_called_once_with(label="ticket")
    assert sorted(run.result) == ["email", "ticket"]
