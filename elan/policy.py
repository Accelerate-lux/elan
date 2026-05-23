from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WorkflowPolicy(BaseModel):
    """Runtime governance policy for workflow execution."""

    model_config = ConfigDict(frozen=True)

    max_parallel_tasks: int | None = Field(default=None, ge=1)
    allow_runtime_expansion: bool = False
    allow_cycles: bool = False

    def allows(self, child: "WorkflowPolicy") -> bool:
        return (
            _limit_allows(self.max_parallel_tasks, child.max_parallel_tasks)
            and _bool_allows(self.allow_runtime_expansion, child.allow_runtime_expansion)
            and _bool_allows(self.allow_cycles, child.allow_cycles)
        )


def _limit_allows(parent: int | None, child: int | None) -> bool:
    if parent is None:
        return True
    if child is None:
        return False
    return child <= parent


def _bool_allows(parent: bool, child: bool) -> bool:
    return parent or not child


def copy_policy(policy: WorkflowPolicy) -> WorkflowPolicy:
    return policy.model_copy(deep=True)


__all__ = ["WorkflowPolicy"]
