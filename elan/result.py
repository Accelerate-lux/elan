from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class WorkflowRun:
    result: Any = None
    outputs: dict[str, list[Any]] = field(default_factory=dict)
