from dataclasses import dataclass, field
from typing import Any, Literal

from .task import Task


JoinInstanceStatus = Literal["open", "reducing", "settled"]


@dataclass(slots=True)
class JoinInstance:
    id: str
    scope_activation_id: str
    owner_branch_id: str
    active_branch_ids: set[str] = field(default_factory=set)
    contributions: list[Any] = field(default_factory=list)
    status: JoinInstanceStatus = "open"


@dataclass(slots=True)
class JoinState:
    node_name: str
    reducer: Task | None = None
    scope_node_name: str | None = None
    instances: dict[str, JoinInstance] = field(default_factory=dict)
    workflow_contributions: list[Any] = field(default_factory=list)
    finalized: bool = False

    @property
    def is_workflow_scoped(self) -> bool:
        return self.scope_node_name is None
