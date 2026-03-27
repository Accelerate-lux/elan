from dataclasses import dataclass
from typing import Any

from .task import Task


@dataclass(slots=True)
class Node:
    run: Task | str
    next: str | list[str] | dict[str, str] | None = None
    input: dict[str, Any] | None = None
    output: str | list[Any] | None = None
    route_on: str | None = None
