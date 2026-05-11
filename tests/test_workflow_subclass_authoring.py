import pytest
from pydantic import BaseModel

from elan import Input, Join, Node, Workflow, task


@pytest.mark.asyncio
async def test_workflow_subclass_minimal_start(branch_id):
    @task
    def hello():
        return "Hello, world!"

    class HelloWorld(Workflow):
        start = hello

    workflow = HelloWorld()
    run = await workflow.run()

    assert workflow.name == "HelloWorld"
    assert run.result == "Hello, world!"
    assert run.outputs == {
        branch_id[0]: {
            "hello": ["Hello, world!"],
        }
    }


@pytest.mark.asyncio
async def test_workflow_subclass_explicit_name_and_nodes(branch_id):
    @task
    def prepare():
        return "world"

    @task
    def greet(name: str):
        return f"Hello, {name}!"

    greet_task = greet

    class GreetingWorkflow(Workflow):
        name = "greeting"
        start = Node(run=prepare, next="greet")
        greet = greet_task

    workflow = GreetingWorkflow()
    run = await workflow.run()

    assert workflow.name == "greeting"
    assert run.result == "Hello, world!"
    assert run.outputs == {
        branch_id[0]: {
            "prepare": ["world"],
            "greet": ["Hello, world!"],
        }
    }


@pytest.mark.asyncio
async def test_workflow_subclass_context_and_bind_context(branch_id):
    class RunContext(BaseModel):
        label: str

    @task
    def show(context: RunContext) -> str:
        return context.label

    class ContextWorkflow(Workflow):
        context = RunContext
        bind_context = {"label": Input.label}
        start = show

    run = await ContextWorkflow().run(label="ready")

    assert run.result == "ready"
    assert run.outputs == {
        branch_id[0]: {
            "show": ["ready"],
        }
    }


@pytest.mark.asyncio
async def test_workflow_subclass_inherits_and_overrides_declarations(branch_id):
    @task
    def prepare():
        return "world"

    @task
    def greet(name: str):
        return f"Hello, {name}!"

    @task
    def shout(name: str):
        return f"HELLO, {name.upper()}!"

    greet_task = greet
    shout_task = shout

    class BaseGreeting(Workflow):
        name = "base"
        start = Node(run=prepare, next="greet")
        greet = greet_task

    class LoudGreeting(BaseGreeting):
        name = "loud"
        greet = shout_task

    workflow = LoudGreeting()
    run = await workflow.run()

    assert workflow.name == "loud"
    assert run.result == "HELLO, WORLD!"
    assert run.outputs == {
        branch_id[0]: {
            "prepare": ["world"],
            "shout": ["HELLO, WORLD!"],
        }
    }


@pytest.mark.asyncio
async def test_workflow_subclass_collects_join_result(branch_id):
    @task
    def load_values():
        yield 1
        yield 2

    @task
    def collect(values: list[int]) -> int:
        return sum(values)

    class SumWorkflow(Workflow):
        start = Node(run=load_values, next="result")
        result = Join(run=collect)

    run = await SumWorkflow().run()

    assert run.result == 3
    assert run.outputs == {
        branch_id[0]: {
            "load_values": [[1, 2]],
        },
    }


def test_workflow_subclass_ignores_non_node_public_constants():
    @task
    def hello():
        return "Hello, world!"

    class HelloWorld(Workflow):
        retries = 3
        enabled = True

        def helper(self):
            return "ignored"

        start = hello

    workflow = HelloWorld()

    assert workflow.nodes == {}


def test_workflow_subclass_missing_start_fails_clearly():
    class MissingStart(Workflow):
        pass

    with pytest.raises(TypeError, match="must declare 'start'"):
        MissingStart()


def test_workflow_subclass_rejects_constructor_arguments():
    @task
    def hello():
        return "Hello, world!"

    class HelloWorld(Workflow):
        start = hello

    with pytest.raises(TypeError, match="does not accept constructor arguments"):
        HelloWorld("hello_world", start=hello)


def test_workflow_subclass_invalid_context_reuses_constructor_validation():
    class RunContext(BaseModel):
        locale: str = "en"

    @task
    def hello():
        return "Hello, world!"

    class InvalidContext(Workflow):
        context = RunContext()
        start = hello

    with pytest.raises(
        TypeError,
        match="Workflow context must be a Pydantic model class or None",
    ):
        InvalidContext()


def test_workflow_subclass_invalid_join_placement_reuses_constructor_validation():
    @task
    def hello():
        return "Hello, world!"

    class InvalidJoin(Workflow):
        start = hello
        collect = Join()

    with pytest.raises(TypeError, match="only allows Join"):
        InvalidJoin()
