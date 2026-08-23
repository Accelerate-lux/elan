from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ._refs import ModelFieldRef
from .node import Node
from .task import Task
from .when import When

if TYPE_CHECKING:
    from .expand import Expand


@dataclass(slots=True)
class Join:
    run: Task | str | None = None
    scope: str | Node | None = None
    next: str | list[str | When] | dict[str, str] | Expand | None = None
    bind_output: str | list[Any] | None = None
    route_on: str | ModelFieldRef | None = None
