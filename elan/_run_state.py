from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from typing import Any

from pydantic import BaseModel

from ._activation import Activation
from ._branch import Branch
from ._graph_state import GraphState

if TYPE_CHECKING:
    from .workflow import Workflow


@dataclass(slots=True)
class RunState:
    workflow: "Workflow"
    graph: GraphState
    workflow_input: dict[str, Any] = field(default_factory=dict)
    context_value: BaseModel | None = None
    result: Any = None
    last_output: Any = None
    outputs: dict[str, list[Any]] = field(default_factory=dict)
    branches: dict[str, Branch] = field(default_factory=dict)
    activations: dict[str, Activation] = field(default_factory=dict)
    status: str = "created"
    _branch_counter: int = 0
    _activation_counter: int = 0
