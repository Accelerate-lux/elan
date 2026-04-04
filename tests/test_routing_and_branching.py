import asyncio

import pytest
from pydantic import BaseModel

from elan import Join, Node, When, Workflow, ref
from elan._refs import ModelFieldRef


@ref
class RoutePayload(BaseModel):
    name: str
    style: str
    should_email: bool
    should_notify: bool


@ref
class OtherRoutePayload(BaseModel):
    name: str
    style: str
    should_email: bool


class SubRoutePayload(RoutePayload):
    pass


@pytest.mark.asyncio
async def test_run_workflow_exclusive_branch_from_named_payload(mock_task_factory, branch_id):
    def _prepare():
        return "world", "formal"

    async def _greet_formal(name: str):
        return f"Hello, {name}."

    async def _greet_casual(name: str):
        return f"Hey {name}!"

    prepare = mock_task_factory(_prepare)
    greet_formal = mock_task_factory(_greet_formal)
    greet_casual = mock_task_factory(_greet_casual)

    workflow = Workflow(
        "branching_greet",
        start=Node(
            run=prepare,
            bind_output=["name", "style"],
            route_on="style",
            next={
                "formal": "greet_formal",
                "casual": "greet_casual",
            },
        ),
        greet_formal=greet_formal,
        greet_casual=greet_casual,
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet_formal.mock.assert_called_once_with(name="world")
    greet_casual.mock.assert_not_called()
    assert run.result is None
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": [("world", "formal")],
            "_greet_formal": ["Hello, world."],
        }
    }


@pytest.mark.asyncio
async def test_run_workflow_exclusive_branch_from_raw_dict(mock_task_factory, branch_id):
    def _prepare():
        return {"style": "formal", "name": "world"}

    async def _greet_formal(payload: dict[str, str]):
        return f"Hello, {payload['name']}."

    async def _greet_casual(payload: dict[str, str]):
        return f"Hey {payload['name']}!"

    prepare = mock_task_factory(_prepare)
    greet_formal = mock_task_factory(_greet_formal)
    greet_casual = mock_task_factory(_greet_casual)

    workflow = Workflow(
        "branching_greet",
        start=Node(
            run=prepare,
            route_on="style",
            next={
                "formal": "greet_formal",
                "casual": "greet_casual",
            },
        ),
        greet_formal=greet_formal,
        greet_casual=greet_casual,
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet_formal.mock.assert_called_once_with({"style": "formal", "name": "world"})
    greet_casual.mock.assert_not_called()
    assert run.result is None
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": [{"style": "formal", "name": "world"}],
            "_greet_formal": ["Hello, world."],
        }
    }


@pytest.mark.asyncio
async def test_run_workflow_exclusive_branch_from_registered_ref_model(
    mock_task_factory,
    branch_id,
):
    def _prepare() -> RoutePayload:
        return RoutePayload(
            name="world",
            style="formal",
            should_email=True,
            should_notify=False,
        )

    async def _greet_formal(payload: RoutePayload):
        return f"Hello, {payload.name}."

    async def _greet_casual(payload: RoutePayload):
        return f"Hey {payload.name}!"

    prepare = mock_task_factory(_prepare)
    greet_formal = mock_task_factory(_greet_formal)
    greet_casual = mock_task_factory(_greet_casual)

    workflow = Workflow(
        "branching_greet",
        start=Node(
            run=prepare,
            route_on=RoutePayload.style,
            next={
                "formal": "greet_formal",
                "casual": "greet_casual",
            },
        ),
        greet_formal=greet_formal,
        greet_casual=greet_casual,
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet_formal.mock.assert_called_once()
    greet_casual.mock.assert_not_called()
    assert run.result is None
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": [
                RoutePayload(
                    name="world",
                    style="formal",
                    should_email=True,
                    should_notify=False,
                )
            ],
            "_greet_formal": ["Hello, world."],
        }
    }


@pytest.mark.asyncio
async def test_run_workflow_exclusive_branch_accepts_ref_model_subclass(
    mock_task_factory,
    branch_id,
):
    def _prepare() -> SubRoutePayload:
        return SubRoutePayload(
            name="world",
            style="formal",
            should_email=True,
            should_notify=False,
        )

    async def _greet_formal(payload: RoutePayload):
        return f"Hello, {payload.name}."

    prepare = mock_task_factory(_prepare)
    greet_formal = mock_task_factory(_greet_formal)

    workflow = Workflow(
        "branching_greet",
        start=Node(
            run=prepare,
            route_on=RoutePayload.style,
            next={"formal": "greet_formal"},
        ),
        greet_formal=greet_formal,
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet_formal.mock.assert_called_once()
    assert run.result is None
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": [
                SubRoutePayload(
                    name="world",
                    style="formal",
                    should_email=True,
                    should_notify=False,
                )
            ],
            "_greet_formal": ["Hello, world."],
        }
    }


@pytest.mark.asyncio
async def test_run_workflow_when_from_named_payload(mock_task_factory, branch_id):
    def _prepare():
        return "world", True

    async def _send_email(name: str):
        return f"email:{name}"

    prepare = mock_task_factory(_prepare)
    send_email = mock_task_factory(_send_email)

    workflow = Workflow(
        "conditional_routes",
        start=Node(
            run=prepare,
            bind_output=["name", "should_email"],
            next=[When("should_email", "send_email")],
        ),
        send_email=send_email,
    )

    run = await workflow.run()

    send_email.mock.assert_called_once_with(name="world")
    assert run.result is None
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": [("world", True)],
        },
        branch_id[1]: {
            "_send_email": ["email:world"],
        },
    }


@pytest.mark.asyncio
async def test_run_workflow_when_from_raw_dict(mock_task_factory, branch_id):
    def _prepare():
        return {"name": "world", "should_email": True}

    async def _send_email(payload: dict[str, object]):
        return f"email:{payload['name']}"

    prepare = mock_task_factory(_prepare)
    send_email = mock_task_factory(_send_email)

    workflow = Workflow(
        "conditional_routes",
        start=Node(
            run=prepare,
            next=[When("should_email", "send_email")],
        ),
        send_email=send_email,
    )

    run = await workflow.run()

    send_email.mock.assert_called_once_with(
        {"name": "world", "should_email": True}
    )
    assert run.result is None
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": [{"name": "world", "should_email": True}],
        },
        branch_id[1]: {
            "_send_email": ["email:world"],
        },
    }


@pytest.mark.asyncio
async def test_run_workflow_when_from_registered_ref_model(mock_task_factory, branch_id):
    def _prepare() -> RoutePayload:
        return RoutePayload(
            name="world",
            style="formal",
            should_email=True,
            should_notify=False,
        )

    async def _send_email(name: str):
        return f"email:{name}"

    prepare = mock_task_factory(_prepare)
    send_email = mock_task_factory(_send_email)

    workflow = Workflow(
        "conditional_routes",
        start=Node(
            run=prepare,
            next=[When(RoutePayload.should_email, "send_email")],
        ),
        send_email=send_email,
    )

    run = await workflow.run()

    send_email.mock.assert_called_once_with(name="world")
    assert run.result is None
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": [
                RoutePayload(
                    name="world",
                    style="formal",
                    should_email=True,
                    should_notify=False,
                )
            ],
        },
        branch_id[1]: {
            "_send_email": ["email:world"],
        },
    }


@pytest.mark.asyncio
async def test_run_workflow_when_list_target(mock_task_factory, branch_id):
    def _prepare():
        return "world", True

    async def _send_email(name: str):
        return f"email:{name}"

    async def _notify(name: str):
        return f"notify:{name}"

    prepare = mock_task_factory(_prepare)
    send_email = mock_task_factory(_send_email)
    notify = mock_task_factory(_notify)

    workflow = Workflow(
        "conditional_routes",
        start=Node(
            run=prepare,
            bind_output=["name", "should_notify"],
            next=[When("should_notify", ["send_email", "notify"])],
        ),
        send_email=send_email,
        notify=notify,
    )

    run = await workflow.run()

    send_email.mock.assert_called_once_with(name="world")
    notify.mock.assert_called_once_with(name="world")
    assert run.result is None
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": [("world", True)],
        },
        branch_id[1]: {
            "_send_email": ["email:world"],
        },
        branch_id[2]: {
            "_notify": ["notify:world"],
        },
    }


@pytest.mark.asyncio
async def test_run_workflow_multiple_when_matches(mock_task_factory, branch_id):
    def _prepare() -> RoutePayload:
        return RoutePayload(
            name="world",
            style="formal",
            should_email=True,
            should_notify=True,
        )

    async def _send_email(name: str):
        return f"email:{name}"

    async def _notify(name: str):
        return f"notify:{name}"

    prepare = mock_task_factory(_prepare)
    send_email = mock_task_factory(_send_email)
    notify = mock_task_factory(_notify)

    workflow = Workflow(
        "conditional_routes",
        start=Node(
            run=prepare,
            next=[
                When(RoutePayload.should_email, "send_email"),
                When(RoutePayload.should_notify, "notify"),
            ],
        ),
        send_email=send_email,
        notify=notify,
    )

    run = await workflow.run()

    send_email.mock.assert_called_once_with(name="world")
    notify.mock.assert_called_once_with(name="world")
    assert run.result is None
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": [
                RoutePayload(
                    name="world",
                    style="formal",
                    should_email=True,
                    should_notify=True,
                )
            ],
        },
        branch_id[1]: {
            "_send_email": ["email:world"],
        },
        branch_id[2]: {
            "_notify": ["notify:world"],
        },
    }


@pytest.mark.asyncio
async def test_run_workflow_zero_when_matches_is_valid(mock_task_factory, branch_id):
    def _prepare():
        return "world", False

    async def _send_email(name: str):
        return f"email:{name}"

    prepare = mock_task_factory(_prepare)
    send_email = mock_task_factory(_send_email)

    workflow = Workflow(
        "conditional_routes",
        start=Node(
            run=prepare,
            bind_output=["name", "should_email"],
            next=[When("should_email", "send_email")],
        ),
        send_email=send_email,
    )

    run = await workflow.run()

    send_email.mock.assert_not_called()
    assert run.result is None
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": [("world", False)],
        },
    }


@pytest.mark.asyncio
async def test_run_workflow_duplicate_when_destinations_are_allowed(
    mock_task_factory,
    branch_id,
):
    def _prepare():
        return "world", True, True

    async def _send_email(name: str):
        return f"email:{name}"

    prepare = mock_task_factory(_prepare)
    send_email = mock_task_factory(_send_email)

    workflow = Workflow(
        "conditional_routes",
        start=Node(
            run=prepare,
            bind_output=["name", "should_email", "should_notify"],
            next=[
                When("should_email", "send_email"),
                When("should_notify", "send_email"),
            ],
        ),
        send_email=send_email,
    )

    run = await workflow.run()

    assert send_email.mock.call_count == 2
    assert run.result is None
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": [("world", True, True)],
        },
        branch_id[1]: {
            "_send_email": ["email:world"],
        },
        branch_id[2]: {
            "_send_email": ["email:world"],
        },
    }


@pytest.mark.asyncio
async def test_run_workflow_missing_route_on_fails_clearly(mock_task_factory):
    def _prepare():
        return "world", "formal"

    async def _greet_formal(name: str):
        return f"Hello, {name}."

    prepare = mock_task_factory(_prepare)
    greet_formal = mock_task_factory(_greet_formal)

    workflow = Workflow(
        "branching_greet",
        start=Node(
            run=prepare,
            bind_output=["name", "style"],
            next={"formal": "greet_formal"},
        ),
        greet_formal=greet_formal,
    )

    with pytest.raises(TypeError, match="route_on"):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_route_on_ref_non_model_value_fails_clearly(
    mock_task_factory,
):
    def _prepare():
        return "world", "formal"

    async def _greet_formal(name: str):
        return f"Hello, {name}."

    prepare = mock_task_factory(_prepare)
    greet_formal = mock_task_factory(_greet_formal)

    workflow = Workflow(
        "branching_greet",
        start=Node(
            run=prepare,
            bind_output=["name", "style"],
            route_on=RoutePayload.style,
            next={"formal": "greet_formal"},
        ),
        greet_formal=greet_formal,
    )

    with pytest.raises(
        TypeError,
        match="cannot use route_on='RoutePayload.style' with value of type _MappedPayload",
    ):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_route_on_ref_wrong_model_type_fails_clearly(
    mock_task_factory,
):
    def _prepare() -> OtherRoutePayload:
        return OtherRoutePayload(name="world", style="formal", should_email=True)

    async def _greet_formal(payload: RoutePayload):
        return f"Hello, {payload.name}."

    prepare = mock_task_factory(_prepare)
    greet_formal = mock_task_factory(_greet_formal)

    workflow = Workflow(
        "branching_greet",
        start=Node(
            run=prepare,
            route_on=RoutePayload.style,
            next={"formal": "greet_formal"},
        ),
        greet_formal=greet_formal,
    )

    with pytest.raises(
        TypeError,
        match="cannot use route_on='RoutePayload.style' with model value of type OtherRoutePayload",
    ):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_route_on_ref_missing_field_fails_clearly(
    mock_task_factory,
):
    def _prepare() -> RoutePayload:
        return RoutePayload(
            name="world",
            style="formal",
            should_email=True,
            should_notify=False,
        )

    async def _greet_formal(payload: RoutePayload):
        return f"Hello, {payload.name}."

    prepare = mock_task_factory(_prepare)
    greet_formal = mock_task_factory(_greet_formal)

    workflow = Workflow(
        "branching_greet",
        start=Node(
            run=prepare,
            route_on=ModelFieldRef(model=RoutePayload, field_name="missing"),
            next={"formal": "greet_formal"},
        ),
        greet_formal=greet_formal,
    )

    with pytest.raises(TypeError, match="route source does not provide field 'missing'"):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_route_on_missing_field_fails_clearly(mock_task_factory):
    def _prepare():
        return "world"

    async def _greet_formal(name: str):
        return f"Hello, {name}."

    prepare = mock_task_factory(_prepare)
    greet_formal = mock_task_factory(_greet_formal)

    workflow = Workflow(
        "branching_greet",
        start=Node(
            run=prepare,
            bind_output="name",
            route_on="style",
            next={"formal": "greet_formal"},
        ),
        greet_formal=greet_formal,
    )

    with pytest.raises(TypeError, match="does not provide field 'style'"):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_when_missing_string_condition_field_fails_clearly(
    mock_task_factory,
):
    def _prepare():
        return "world"

    async def _send_email(name: str):
        return f"email:{name}"

    prepare = mock_task_factory(_prepare)
    send_email = mock_task_factory(_send_email)

    workflow = Workflow(
        "conditional_routes",
        start=Node(
            run=prepare,
            bind_output="name",
            next=[When("should_email", "send_email")],
        ),
        send_email=send_email,
    )

    with pytest.raises(TypeError, match="condition source does not provide field 'should_email'"):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_when_missing_ref_condition_field_fails_clearly(
    mock_task_factory,
):
    def _prepare() -> RoutePayload:
        return RoutePayload(
            name="world",
            style="formal",
            should_email=True,
            should_notify=False,
        )

    async def _send_email(name: str):
        return f"email:{name}"

    prepare = mock_task_factory(_prepare)
    send_email = mock_task_factory(_send_email)

    workflow = Workflow(
        "conditional_routes",
        start=Node(
            run=prepare,
            next=[When(ModelFieldRef(model=RoutePayload, field_name="missing"), "send_email")],
        ),
        send_email=send_email,
    )

    with pytest.raises(TypeError, match="does not provide field 'missing'"):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_route_on_unmapped_value_fails_clearly(mock_task_factory):
    def _prepare():
        return "world", "unknown"

    async def _greet_formal(name: str):
        return f"Hello, {name}."

    prepare = mock_task_factory(_prepare)
    greet_formal = mock_task_factory(_greet_formal)

    workflow = Workflow(
        "branching_greet",
        start=Node(
            run=prepare,
            bind_output=["name", "style"],
            route_on="style",
            next={"formal": "greet_formal"},
        ),
        greet_formal=greet_formal,
    )

    with pytest.raises(KeyError, match="does not define a route for value 'unknown'"):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_route_on_ref_unmapped_value_fails_clearly(mock_task_factory):
    def _prepare() -> RoutePayload:
        return RoutePayload(
            name="world",
            style="unknown",
            should_email=True,
            should_notify=False,
        )

    async def _greet_formal(payload: RoutePayload):
        return f"Hello, {payload.name}."

    prepare = mock_task_factory(_prepare)
    greet_formal = mock_task_factory(_greet_formal)

    workflow = Workflow(
        "branching_greet",
        start=Node(
            run=prepare,
            route_on=RoutePayload.style,
            next={"formal": "greet_formal"},
        ),
        greet_formal=greet_formal,
    )

    with pytest.raises(KeyError, match="does not define a route for value 'unknown'"):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_when_non_bool_condition_fails_clearly(mock_task_factory):
    def _prepare():
        return "world", "yes"

    async def _send_email(name: str):
        return f"email:{name}"

    prepare = mock_task_factory(_prepare)
    send_email = mock_task_factory(_send_email)

    workflow = Workflow(
        "conditional_routes",
        start=Node(
            run=prepare,
            bind_output=["name", "should_email"],
            next=[When("should_email", "send_email")],
        ),
        send_email=send_email,
    )

    with pytest.raises(TypeError, match="requires When condition 'should_email' to resolve to bool"):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_branch_mapping_unknown_node_fails_clearly(mock_task_factory):
    def _prepare():
        return "world", "formal"

    prepare = mock_task_factory(_prepare)

    workflow = Workflow(
        "branching_greet",
        start=Node(
            run=prepare,
            bind_output=["name", "style"],
            route_on="style",
            next={"formal": "missing"},
        ),
    )

    with pytest.raises(KeyError, match="references unknown node 'missing'"):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_route_on_ref_unknown_target_node_fails_clearly(
    mock_task_factory,
):
    def _prepare() -> RoutePayload:
        return RoutePayload(
            name="world",
            style="formal",
            should_email=True,
            should_notify=False,
        )

    prepare = mock_task_factory(_prepare)

    workflow = Workflow(
        "branching_greet",
        start=Node(
            run=prepare,
            route_on=RoutePayload.style,
            next={"formal": "missing"},
        ),
    )

    with pytest.raises(KeyError, match="references unknown node 'missing'"):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_when_unknown_destination_node_fails_clearly(
    mock_task_factory,
):
    def _prepare():
        return "world", True

    prepare = mock_task_factory(_prepare)

    workflow = Workflow(
        "conditional_routes",
        start=Node(
            run=prepare,
            bind_output=["name", "should_email"],
            next=[When("should_email", "missing")],
        ),
    )

    with pytest.raises(KeyError, match="references unknown node 'missing'"):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_mixed_next_list_is_evaluated_in_order(
    mock_task_factory,
    branch_id,
):
    def _prepare():
        return "world", True

    async def _send_email(name: str):
        return f"email:{name}"

    async def _notify(name: str):
        return f"notify:{name}"

    prepare = mock_task_factory(_prepare)
    send_email = mock_task_factory(_send_email)
    notify = mock_task_factory(_notify)

    run = await Workflow(
        "conditional_routes",
        start=Node(
            run=prepare,
            bind_output=["name", "should_email"],
            next=["send_email", When("should_email", "notify")],
        ),
        send_email=send_email,
        notify=notify,
    ).run()

    send_email.mock.assert_called_once_with(name="world")
    notify.mock.assert_called_once_with(name="world")
    assert run.result is None
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": [("world", True)],
        },
        branch_id[1]: {
            "_send_email": ["email:world"],
        },
        branch_id[2]: {
            "_notify": ["notify:world"],
        },
    }


@pytest.mark.asyncio
async def test_run_workflow_fan_out_duplicates_payload(mock_task_factory, branch_id):
    def _prepare():
        return "world"

    async def _greet(name: str):
        return f"Hello, {name}!"

    async def _badge(name: str):
        return f"badge:{name}"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)
    badge = mock_task_factory(_badge)

    workflow = Workflow(
        "fan_out_profile",
        start=Node(
            run=prepare,
            bind_output="name",
            next=["greet", "badge"],
        ),
        greet=greet,
        badge=badge,
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with(name="world")
    badge.mock.assert_called_once_with(name="world")
    assert run.result is None
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": ["world"],
        },
        branch_id[1]: {
            "_greet": ["Hello, world!"],
        },
        branch_id[2]: {
            "_badge": ["badge:world"],
        },
    }


@pytest.mark.asyncio
async def test_run_workflow_fan_out_with_reserved_result_is_invalid(mock_task_factory):
    def _prepare():
        return "world"

    async def _greet(name: str):
        return f"Hello, {name}!"

    def _identity(value: str):
        return value

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)
    identity = mock_task_factory(_identity)

    workflow = Workflow(
        "fan_out_profile",
        start=Node(
            run=prepare,
            bind_output="name",
            next=["greet"],
        ),
        greet=Node(run=greet, next="result"),
        result=Node(run=identity),
    )

    with pytest.raises(NotImplementedError, match="List-based branching with reserved result"):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_fan_out_with_join_result_is_valid(mock_task_factory, branch_id):
    def _prepare():
        return "world"

    async def _greet(name: str):
        return f"Hello, {name}!"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    run = await Workflow(
        "fan_out_profile",
        start=Node(
            run=prepare,
            bind_output="name",
            next=["greet"],
        ),
        greet=Node(run=greet, next="result"),
        result=Join(),
    ).run()

    greet.mock.assert_called_once_with(name="world")
    assert run.result == ["Hello, world!"]
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": ["world"],
        },
        branch_id[1]: {
            "_greet": ["Hello, world!"],
        },
    }


@pytest.mark.asyncio
async def test_run_workflow_when_with_reserved_result_is_invalid(mock_task_factory):
    def _prepare():
        return "world", True

    async def _send_email(name: str):
        return f"email:{name}"

    def _identity(value: str):
        return value

    prepare = mock_task_factory(_prepare)
    send_email = mock_task_factory(_send_email)
    identity = mock_task_factory(_identity)

    workflow = Workflow(
        "conditional_routes",
        start=Node(
            run=prepare,
            bind_output=["name", "should_email"],
            next=[When("should_email", "send_email")],
        ),
        send_email=Node(run=send_email, next="result"),
        result=Node(run=identity),
    )

    with pytest.raises(
        NotImplementedError,
        match="List-based branching with reserved result",
    ):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_when_with_join_result_is_valid(mock_task_factory, branch_id):
    def _prepare():
        return "world", True

    async def _send_email(name: str):
        return f"email:{name}"

    prepare = mock_task_factory(_prepare)
    send_email = mock_task_factory(_send_email)

    run = await Workflow(
        "conditional_routes",
        start=Node(
            run=prepare,
            bind_output=["name", "should_email"],
            next=[When("should_email", "send_email")],
        ),
        send_email=Node(run=send_email, next="result"),
        result=Join(),
    ).run()

    send_email.mock.assert_called_once_with(name="world")
    assert run.result == ["email:world"]
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": [("world", True)],
        },
        branch_id[1]: {
            "_send_email": ["email:world"],
        },
    }


@pytest.mark.asyncio
async def test_run_workflow_when_ref_condition_wrong_model_type_fails_clearly(
    mock_task_factory,
):
    def _prepare() -> OtherRoutePayload:
        return OtherRoutePayload(name="world", style="formal", should_email=True)

    async def _send_email(name: str):
        return f"email:{name}"

    prepare = mock_task_factory(_prepare)
    send_email = mock_task_factory(_send_email)

    workflow = Workflow(
        "conditional_routes",
        start=Node(
            run=prepare,
            next=[When(RoutePayload.should_email, "send_email")],
        ),
        send_email=send_email,
    )

    with pytest.raises(
        TypeError,
        match="cannot read When condition 'RoutePayload.should_email' from model value of type OtherRoutePayload",
    ):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_branch_ids_are_distinct_for_siblings(mock_task_factory, branch_id):
    def _prepare():
        return "world"

    async def _first(name: str):
        return f"first:{name}"

    async def _second(name: str):
        return f"second:{name}"

    prepare = mock_task_factory(_prepare)
    first = mock_task_factory(_first)
    second = mock_task_factory(_second)

    workflow = Workflow(
        "fan_out_profile",
        start=Node(
            run=prepare,
            bind_output="name",
            next=["first", "second"],
        ),
        first=first,
        second=second,
    )

    run = await workflow.run()

    assert sorted(run.outputs) == [branch_id[0], branch_id[1], branch_id[2]]
    assert run.outputs[branch_id[1]] != run.outputs[branch_id[2]]


def test_run_workflow_fan_out_siblings_can_execute_concurrently(
    mock_task_factory,
    branch_id,
):
    async def _scenario():
        started = 0
        both_started = asyncio.Event()

        async def _prepare():
            return "world"

        async def _greet(name: str):
            nonlocal started
            started += 1
            if started == 2:
                both_started.set()
            try:
                await asyncio.wait_for(both_started.wait(), timeout=0.05)
            except TimeoutError as exc:
                raise AssertionError(
                    "fan-out sibling branches did not execute concurrently"
                ) from exc
            return f"Hello, {name}!"

        async def _badge(name: str):
            nonlocal started
            started += 1
            if started == 2:
                both_started.set()
            try:
                await asyncio.wait_for(both_started.wait(), timeout=0.05)
            except TimeoutError as exc:
                raise AssertionError(
                    "fan-out sibling branches did not execute concurrently"
                ) from exc
            return f"badge:{name}"

        prepare = mock_task_factory(_prepare)
        greet = mock_task_factory(_greet)
        badge = mock_task_factory(_badge)

        return await Workflow(
            "fan_out_profile",
            start=Node(
                run=prepare,
                bind_output="name",
                next=["greet", "badge"],
            ),
            greet=greet,
            badge=badge,
        ).run()

    run = asyncio.run(_scenario())

    assert run.result is None
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": ["world"],
        },
        branch_id[1]: {
            "_greet": ["Hello, world!"],
        },
        branch_id[2]: {
            "_badge": ["badge:world"],
        },
    }


def test_run_workflow_multiple_when_matches_can_execute_concurrently(
    mock_task_factory,
    branch_id,
):
    async def _scenario():
        started = 0
        both_started = asyncio.Event()

        def _prepare() -> RoutePayload:
            return RoutePayload(
                name="world",
                style="formal",
                should_email=True,
                should_notify=True,
            )

        async def _send_email(name: str):
            nonlocal started
            started += 1
            if started == 2:
                both_started.set()
            try:
                await asyncio.wait_for(both_started.wait(), timeout=0.05)
            except TimeoutError as exc:
                raise AssertionError(
                    "branches from multiple matching When clauses did not execute concurrently"
                ) from exc
            return f"email:{name}"

        async def _send_notification(name: str):
            nonlocal started
            started += 1
            if started == 2:
                both_started.set()
            try:
                await asyncio.wait_for(both_started.wait(), timeout=0.05)
            except TimeoutError as exc:
                raise AssertionError(
                    "branches from multiple matching When clauses did not execute concurrently"
                ) from exc
            return f"notify:{name}"

        prepare = mock_task_factory(_prepare)
        send_email = mock_task_factory(_send_email)
        send_notification = mock_task_factory(_send_notification)

        return await Workflow(
            "conditional_routes",
            start=Node(
                run=prepare,
                next=[
                    When(RoutePayload.should_email, "send_email"),
                    When(RoutePayload.should_notify, "send_notification"),
                ],
            ),
            send_email=send_email,
            send_notification=send_notification,
        ).run()

    run = asyncio.run(_scenario())

    assert run.result is None
    assert run.outputs == {
        branch_id[0]: {
            "_prepare": [
                RoutePayload(
                    name="world",
                    style="formal",
                    should_email=True,
                    should_notify=True,
                )
            ],
        },
        branch_id[1]: {
            "_send_email": ["email:world"],
        },
        branch_id[2]: {
            "_send_notification": ["notify:world"],
        },
    }

