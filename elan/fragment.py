from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Mapping

from .join import Join
from .node import Node
from .task import Task

if TYPE_CHECKING:
    from .workflow import Workflow


class Fragment:
    """A reusable, self-routed graph fragment materialized by :class:`Expand`."""

    __slots__ = ("start", "nodes")

    def __init__(
        self,
        start: Task | str | Node | "Workflow",
        **nodes: Task | str | Node | Join | "Workflow",
    ) -> None:
        if isinstance(start, Join):
            raise TypeError("Fragment start must be executable, not Join(...).")
        if "result" in nodes:
            raise TypeError(
                "Fragment cannot declare local node 'result'; it is reserved for the workflow result."
            )

        _validate_declaration("start", start, allow_join=False)
        for name, value in nodes.items():
            _validate_declaration(name, value, allow_join=True)

        self.start = start
        self.nodes: Mapping[str, Task | str | Node | Join | Workflow] = (
            MappingProxyType(dict(nodes))
        )


def _validate_declaration(name: str, value: Any, *, allow_join: bool) -> None:
    from .workflow import Workflow

    accepted = (Task, str, Node, Workflow)
    if isinstance(value, accepted) or (allow_join and isinstance(value, Join)):
        return
    raise TypeError(
        f"Fragment node '{name}' must be a task, task name, Node, child Workflow"
        + (", or Join." if allow_join else ".")
    )


__all__ = ["Fragment"]
