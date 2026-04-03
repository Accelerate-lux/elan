from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ._refs import ModelFieldRef
from .task import Task
from .when import When


@dataclass(slots=True)
class Node:
    run: Task | str
    next: str | list[str | When] | dict[str, str] | None = None
    bind_input: dict[str, Any] | None = None
    bind_output: str | list[Any] | None = None
    route_on: str | ModelFieldRef | None = None
