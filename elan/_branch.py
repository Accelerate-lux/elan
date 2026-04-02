from dataclasses import dataclass

from .node import Node
from .task import Task


@dataclass(slots=True)
class Branch:
    id: str
    current: Task | str | Node
    _is_entry: bool = False

    @property
    def is_entry(self) -> bool:
        return self._is_entry

    def advance_to(self, next_node: Task | str | Node) -> None:
        self.current = next_node
        self._is_entry = False
