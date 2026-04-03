import pytest
from pydantic import BaseModel

from elan import Context, Input, Node, Upstream, Workflow, ref


@pytest.mark.asyncio
async def test_run_workflow_two_tasks_mapped_output(mock_task_factory):
    def _prepare():
        return "world"

    async def _greet(name):
        return f"Hello, {name}!"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, bind_output="name", next="greet"),
        greet=greet,
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with(name="world")
    assert run.result == "Hello, world!"
    assert run.outputs == {
        "_prepare": ["world"],
        "_greet": ["Hello, world!"],
    }


@pytest.mark.asyncio
async def test_run_workflow_two_tasks_discard_output(mock_task_factory):
    def _prepare():
        return "ignored", "world"

    async def _greet(name):
        return f"Hello, {name}!"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, bind_output=[..., "name"], next="greet"),
        greet=greet,
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with(name="world")
    assert run.result == "Hello, world!"
    assert run.outputs == {
        "_prepare": [("ignored", "world")],
        "_greet": ["Hello, world!"],
    }


@pytest.mark.asyncio
async def test_run_workflow_tuple_output(mock_task_factory):
    def _prepare():
        return "hello", "world"

    async def _greet(prefix: str, name: str):
        return f"{prefix.title()}, {name}!"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, next="greet"),
        greet=greet,
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with("hello", "world")
    assert run.result == "Hello, world!"
    assert run.outputs == {
        "_prepare": [("hello", "world")],
        "_greet": ["Hello, world!"],
    }


@pytest.mark.asyncio
async def test_run_workflow_tuple_output_arity_mismatch(mock_task_factory):
    def _prepare():
        return "hello", "world"

    async def _greet(name: str):
        return f"Hello, {name}!"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, next="greet"),
        greet=greet,
    )

    with pytest.raises(TypeError, match="tuple output of length 2"):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_tuple_output_type_mismatch(mock_task_factory):
    def _prepare():
        return ("world",)

    async def _greet(count: int):
        return f"Hello x{count}"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, next="greet"),
        greet=greet,
    )

    with pytest.raises(TypeError, match="parameter 'count'"):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_list_output_is_opaque(mock_task_factory):
    def _prepare():
        return ["hello", "world"]

    async def _greet(values: list[str]):
        return f"{values[0].title()}, {values[1]}!"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, next="greet"),
        greet=greet,
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with(["hello", "world"])
    assert run.result == "Hello, world!"
    assert run.outputs == {
        "_prepare": [["hello", "world"]],
        "_greet": ["Hello, world!"],
    }


@pytest.mark.asyncio
async def test_run_workflow_raw_dict_output_is_opaque(mock_task_factory):
    def _prepare():
        return {"name": "world"}

    async def _greet(payload: dict[str, str]):
        return f"Hello, {payload['name']}!"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, next="greet"),
        greet=greet,
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with({"name": "world"})
    assert run.result == "Hello, world!"
    assert run.outputs == {
        "_prepare": [{"name": "world"}],
        "_greet": ["Hello, world!"],
    }


@pytest.mark.asyncio
async def test_run_workflow_raw_dict_output_does_not_unpack(mock_task_factory):
    def _prepare():
        return {"name": "world"}

    async def _greet(name: str):
        return f"Hello, {name}!"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, next="greet"),
        greet=greet,
    )

    with pytest.raises(TypeError, match="annotation <class 'str'>"):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_literal_input_injection(mock_task_factory):
    def _prepare():
        return "world"

    async def _greet(name: str, punctuation: str):
        return f"Hello, {name}{punctuation}"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, next="greet"),
        greet=Node(run=greet, bind_input={"punctuation": "!"}),
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with(name="world", punctuation="!")
    assert run.result == "Hello, world!"


@pytest.mark.asyncio
async def test_run_workflow_literal_input_overrides_automatic_binding(mock_task_factory):
    def _prepare():
        return "world"

    async def _greet(name: str):
        return f"Hello, {name}!"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, next="greet"),
        greet=Node(run=greet, bind_input={"name": "friend"}),
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with(name="friend")
    assert run.result == "Hello, friend!"


@pytest.mark.asyncio
async def test_run_workflow_literal_input_mixed_with_automatic_binding(mock_task_factory):
    def _prepare():
        return "hello", "world"

    async def _greet(prefix: str, name: str, punctuation: str):
        return f"{prefix.title()}, {name}{punctuation}"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, next="greet"),
        greet=Node(run=greet, bind_input={"punctuation": "!"}),
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with(
        prefix="hello",
        name="world",
        punctuation="!",
    )
    assert run.result == "Hello, world!"


@pytest.mark.asyncio
async def test_run_workflow_literal_input_type_mismatch(mock_task_factory):
    def _prepare():
        return "world"

    async def _greet(count: int):
        return f"Hello x{count}"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, next="greet"),
        greet=Node(run=greet, bind_input={"count": "wrong"}),
    )

    with pytest.raises(TypeError, match="parameter 'count'"):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_literal_input_missing_required_parameter(mock_task_factory):
    async def _greet(name: str, title: str, punctuation: str):
        return f"Hello, {title} {name}{punctuation}"

    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=greet, bind_input={"punctuation": "!"}),
    )

    with pytest.raises(TypeError, match="missing required inputs: title"):
        await workflow.run(name="world")


class GreetingContext(BaseModel):
    punctuation: str = "!"


@ref
class GreetingPayload(BaseModel):
    name: str
    style: str


@pytest.mark.asyncio
async def test_run_workflow_input_ref_binding(mock_task_factory):
    async def _greet(title: str):
        return f"{title} world"

    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=greet, bind_input={"title": Input.title}),
    )

    run = await workflow.run(title="Dr")

    greet.mock.assert_called_once_with(title="Dr")
    assert run.result == "Dr world"


@pytest.mark.asyncio
async def test_run_workflow_context_ref_binding(mock_task_factory):
    def _prepare():
        return "world"

    async def _greet(name: str, punctuation: str):
        return f"Hello, {name}{punctuation}"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, next="greet"),
        context=GreetingContext,
        greet=Node(
            run=greet,
            bind_input={
                "name": "world",
                "punctuation": Context.punctuation,
            },
        ),
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with(name="world", punctuation="!")
    assert run.result == "Hello, world!"


@pytest.mark.asyncio
async def test_run_workflow_upstream_ref_binding_from_mapped_payload(mock_task_factory):
    def _prepare():
        return "hello", "world"

    async def _greet(name: str, style: str):
        return f"{style.title()}, {name}!"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, bind_output=["style", "name"], next="greet"),
        greet=Node(
            run=greet,
            bind_input={
                "name": Upstream.name,
                "style": Upstream.style,
            },
        ),
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with(name="world", style="hello")
    assert run.result == "Hello, world!"


@pytest.mark.asyncio
async def test_run_workflow_upstream_ref_binding_from_registered_model(mock_task_factory):
    def _prepare() -> GreetingPayload:
        return GreetingPayload(name="world", style="hello")

    async def _greet(name: str, style: str):
        return f"{style.title()}, {name}!"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, next="greet"),
        greet=Node(
            run=greet,
            bind_input={
                "name": Upstream.name,
                "style": Upstream.style,
            },
        ),
    )

    run = await workflow.run()

    prepare.mock.assert_called_once_with()
    greet.mock.assert_called_once_with(name="world", style="hello")
    assert run.result == "Hello, world!"


@pytest.mark.asyncio
async def test_run_workflow_upstream_ref_fails_for_opaque_raw_dict(mock_task_factory):
    def _prepare():
        return {"name": "world"}

    async def _greet(name: str):
        return f"Hello, {name}!"

    prepare = mock_task_factory(_prepare)
    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=prepare, next="greet"),
        greet=Node(run=greet, bind_input={"name": Upstream.name}),
    )

    with pytest.raises(TypeError, match="cannot read Upstream.name from value of type dict"):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_input_ref_missing_field(mock_task_factory):
    async def _greet(title: str):
        return title

    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        start=Node(run=greet, bind_input={"title": Input.title}),
    )

    with pytest.raises(TypeError, match="Workflow input does not provide field 'title'"):
        await workflow.run()


@pytest.mark.asyncio
async def test_run_workflow_context_ref_missing_field(mock_task_factory):
    async def _greet(punctuation: str):
        return punctuation

    greet = mock_task_factory(_greet)

    workflow = Workflow(
        "greet_world",
        context=GreetingContext,
        start=Node(run=greet, bind_input={"punctuation": Context.missing}),
    )

    with pytest.raises(TypeError, match="Context does not provide field 'missing'"):
        await workflow.run()
