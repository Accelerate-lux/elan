from dataclasses import dataclass, field

from .node import Node
from .task import Task


@dataclass(slots=True)
class GraphState:
    start: Task | str | Node
    nodes: dict[str, Task | str | Node] = field(default_factory=dict)
