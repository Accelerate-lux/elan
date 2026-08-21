from __future__ import annotations

from dataclasses import dataclass

from .node import Node
from .task import Task


@dataclass(slots=True)
class Join:
    run: Task | str | None = None
    scope: str | Node | None = None
