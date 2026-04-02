from .node import Node
from .task import Task


def resolve_linear_next(
    workflow_name: str,
    next_value: str | list[str] | dict[str, str] | None,
    nodes: dict[str, Task | str | Node],
) -> tuple[str, Task | str | Node] | None:
    if next_value is None:
        return None

    if not isinstance(next_value, str):
        raise NotImplementedError(
            "Only single-string routing is implemented in the initial scaffold."
        )

    if next_value not in nodes:
        raise KeyError(
            f"Workflow '{workflow_name}' references unknown node '{next_value}'."
        )

    return next_value, nodes[next_value]
