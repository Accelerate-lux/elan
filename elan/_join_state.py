from dataclasses import dataclass, field
from typing import Any

from .task import Task


@dataclass(slots=True)
class JoinState:
    reducer: Task | None = None
    contributions: list[Any] = field(default_factory=list)
    finalized: bool = False
