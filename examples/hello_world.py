import asyncio

from elan import Node, Workflow, task


@task
def prepare():
    return "World"


@task
async def greet(name: str):
    return f"Hello, {name}!"


workflow = Workflow(
    "greet_world",
    start=Node(run=prepare, next="greet"),
    greet=greet,
)


if __name__ == "__main__":
    run = asyncio.run(workflow.run())
    print("Result:", run.result)
