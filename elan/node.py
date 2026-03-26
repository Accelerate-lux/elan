from dataclasses import dataclass
from typing import Any, Callable


@dataclass(slots=True)
class Node:
    run: Callable[..., Any]
    next: str | list[str] | dict[str, str] | None = None
    input: dict[str, Any] | None = None
    output: list[Any] | None = None
    route_on: str | None = None
