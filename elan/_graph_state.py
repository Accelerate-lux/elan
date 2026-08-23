from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .join import Join
from .node import Node
from .task import Task

if TYPE_CHECKING:
    from .workflow import Workflow


@dataclass(slots=True)
class GraphState:
    start: Task | str | Node | "Workflow"
    nodes: dict[str, Task | str | Node | Join | "Workflow"] = field(default_factory=dict)
    static_node_names: frozenset[str] = frozenset()
