import pytest
from pydantic import BaseModel

from elan import Binder, Input, Join, Node, When, Workflow, task


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
        bind_context = Binder[RunContext](label=Input.label)
        start = show

    run = await ContextWorkflow().run(label="ready")

    assert run.result == "ready"
    assert run.outputs == {
        branch_id[0]: {
            "show": ["ready"],
        }
    }


@pytest.mark.asyncio
async def test_workflow_subclass_can_override_run_signature(branch_id):
    @task
    def greet(name: str, punctuation: str) -> str:
        return f"Hello, {name}{punctuation}"

    class GreetingWorkflow(Workflow):
        start = greet

        async def run(
            self,
            *,
            name: str = "world",
            punctuation: str = "!",
        ):
            return await self._run(name=name, punctuation=punctuation)

    workflow = GreetingWorkflow()
    run = await workflow.run(name="Ada")

    assert run.result == "Hello, Ada!"
    assert run.outputs == {
        branch_id[0]: {
            "greet": ["Hello, Ada!"],
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
            "collect": [3],
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

    with pytest.raises(TypeError, match="outside.*requires.*scope"):
        InvalidJoin()


@pytest.mark.asyncio
async def test_workflow_subclass_forward_declared_next_target(branch_id):
    @task
    def prepare():
        return "world"

    @task
    def greet(name: str):
        return f"Hello, {name}!"

    greet_task = greet

    class GreetingWorkflow(Workflow):
        greet: Node

        start = Node(run=prepare, next=greet)
        greet = Node(run=greet_task)

    workflow = GreetingWorkflow()
    run = await workflow.run()

    assert workflow.start.next == "greet"
    assert run.result == "Hello, world!"
    assert run.outputs == {
        branch_id[0]: {
            "prepare": ["world"],
            "greet": ["Hello, world!"],
        }
    }


@pytest.mark.asyncio
async def test_workflow_subclass_forward_declared_when_targets(branch_id):
    @task
    def prepare():
        return {"name": "world", "should_email": True}

    @task
    def send_email(payload: dict):
        return f"email:{payload['name']}"

    @task
    def audit(payload: dict):
        return f"audit:{payload['name']}"

    send_email_task = send_email
    audit_task = audit

    class NotificationWorkflow(Workflow):
        send_email: Node
        audit: Node

        start = Node(run=prepare, next=[When("should_email", [send_email, audit])])
        send_email = Node(run=send_email_task)
        audit = Node(run=audit_task)

    run = await NotificationWorkflow().run()

    assert run.result is None
    assert run.outputs == {
        branch_id[0]: {
            "prepare": [{"name": "world", "should_email": True}],
        },
        branch_id[1]: {
            "send_email": ["email:world"],
        },
        branch_id[2]: {
            "audit": ["audit:world"],
        },
    }


@pytest.mark.asyncio
async def test_workflow_subclass_forward_declared_mapping_targets(branch_id):
    @task
    def prepare():
        return {"name": "world", "route": "review"}

    @task
    def review(payload: dict):
        return f"review:{payload['name']}"

    @task
    def reject(payload: dict):
        return f"reject:{payload['name']}"

    review_task = review
    reject_task = reject

    class ReviewWorkflow(Workflow):
        review: Node
        reject: Node

        start = Node(
            run=prepare,
            route_on="route",
            next={
                "review": review,
                "reject": reject,
            },
        )
        review = Node(run=review_task)
        reject = Node(run=reject_task)

    run = await ReviewWorkflow().run()

    assert run.result is None
    assert run.outputs == {
        branch_id[0]: {
            "prepare": [{"name": "world", "route": "review"}],
            "review": ["review:world"],
        }
    }


def test_workflow_subclass_unassigned_forward_declaration_fails_clearly():
    @task
    def prepare():
        return "world"

    class MissingForwardTarget(Workflow):
        review: Node

        start = Node(run=prepare, next=review)

    with pytest.raises(
        TypeError,
        match="forward declares nodes that are not assigned: review",
    ):
        MissingForwardTarget()
