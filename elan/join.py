from __future__ import annotations

from dataclasses import dataclass

from .task import Task


@dataclass(slots=True)
class Join:
    run: Task | str | None = None
