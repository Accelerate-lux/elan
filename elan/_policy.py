from __future__ import annotations

from .policy import WorkflowPolicy, copy_policy


def prepare_policy(
    *,
    workflow_name: str,
    declared_policy: WorkflowPolicy | None,
    inherited_policy: WorkflowPolicy | None,
) -> WorkflowPolicy:
    prepared_policy = _base_policy(
        declared_policy=declared_policy,
        inherited_policy=inherited_policy,
    )

    if inherited_policy is not None and not inherited_policy.allows(prepared_policy):
        raise TypeError(
            f"Workflow '{workflow_name}' policy is not allowed by inherited policy "
            f"'{type(inherited_policy).__name__}'."
        )

    return prepared_policy


def _base_policy(
    *,
    declared_policy: WorkflowPolicy | None,
    inherited_policy: WorkflowPolicy | None,
) -> WorkflowPolicy:
    if declared_policy is not None:
        return copy_policy(declared_policy)

    if inherited_policy is not None:
        return copy_policy(inherited_policy)

    return WorkflowPolicy()
