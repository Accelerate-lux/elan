from dataclasses import dataclass, field
from typing import Any

from .task import Task


@dataclass(slots=True)
class JoinState:
    reducer: Task | None = None
    scope_node_name: str | None = None
    scope_branch_id: str | None = None
    contributions: list[Any] = field(default_factory=list)
    finalized: bool = False

    def bind_scope(self, node_name: str, branch_id: str) -> None:
        if self.scope_node_name != node_name:
            return
        if self.scope_branch_id is not None and self.scope_branch_id != branch_id:
            raise RuntimeError(
                f"Join scope '{node_name}' was activated more than once."
            )
        self.scope_branch_id = branch_id
