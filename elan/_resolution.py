from .node import Node
from .task import Task, resolve_task


def resolve_node(workflow_name: str, value: Task | str | Node) -> Node:
    if isinstance(value, Node):
        return Node(
            run=resolve_task_ref(workflow_name, value.run),
            next=value.next,
            bind_input=value.bind_input,
            bind_output=value.bind_output,
            route_on=value.route_on,
        )

    return Node(run=resolve_task_ref(workflow_name, value))


def resolve_task_ref(workflow_name: str, value: Task | str) -> Task:
    if isinstance(value, Task):
        return value

    if callable(value):
        raise TypeError(
            f"Workflow '{workflow_name}' expects tasks decorated with @task or registered task names; "
            f"got raw callable '{getattr(value, '__name__', repr(value))}'."
        )

    return resolve_task(value)
