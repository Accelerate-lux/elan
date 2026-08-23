from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ._refs import ModelFieldRef
from .binding import Binder
from .task import Task
from .when import When

if TYPE_CHECKING:
    from .expand import Expand
    from .workflow import Workflow


@dataclass(slots=True)
class Node:
    run: Task | str | Workflow
    next: str | list[str | When] | dict[str, str] | Expand | None = None
    bind_input: dict[str, Any] | Binder[Any] | None = None
    bind_output: str | list[Any] | None = None
    context: dict[str, Any] | Binder[Any] | None = None
    route_on: str | ModelFieldRef | None = None
