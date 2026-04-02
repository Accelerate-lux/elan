from dataclasses import dataclass
from typing import Any, Literal

from .node import Node

ActivationStatus = Literal["queued", "running", "settled"]


@dataclass(slots=True)
class Activation:
    id: str
    branch_id: str
    node_name: str | None
    node: Node
    input_value: Any
    is_entry: bool
    status: ActivationStatus = "queued"
    output: Any = None
