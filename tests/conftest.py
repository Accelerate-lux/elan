import inspect
import importlib
from functools import wraps
from unittest.mock import Mock
from uuid import UUID

import pytest

from elan import task

orchestrator_module = importlib.import_module("elan._orchestrator")
Orchestrator = orchestrator_module.Orchestrator
task_module = importlib.import_module("elan.task")
refs_module = importlib.import_module("elan._refs")


@pytest.fixture(autouse=True)
def clear_task_registry():
    task_module._TASKS_BY_KEY.clear()
    task_module._TASKS_BY_ALIAS.clear()
    refs_module._REFS_BY_NAME.clear()
    yield
    task_module._TASKS_BY_KEY.clear()
    task_module._TASKS_BY_ALIAS.clear()
    refs_module._REFS_BY_NAME.clear()


class IdGenerator:
    def __init__(self) -> None:
        self.ids: list[str] = []

    def __iter__(self):
        return self

    def __next__(self) -> str:
        generated_id = str(UUID(int=len(self.ids) + 1))
        self.ids.append(generated_id)
        return generated_id

    def __getitem__(self, key: int) -> str:
        while key >= len(self.ids):
            self.__next__()
        return self.ids[key]


@pytest.fixture(autouse=True)
def branch_id_generator(monkeypatch):
    branch_generator = IdGenerator()
    activation_generator = IdGenerator()

    original_create_branch = Orchestrator._create_branch
    original_create_activation = Orchestrator._create_activation

    def _create_branch(self, *args, **kwargs):
        original_uuid4 = orchestrator_module.uuid4
        orchestrator_module.uuid4 = lambda: next(branch_generator)
        try:
            return original_create_branch(self, *args, **kwargs)
        finally:
            orchestrator_module.uuid4 = original_uuid4

    def _create_activation(self, *args, **kwargs):
        original_uuid4 = orchestrator_module.uuid4
        orchestrator_module.uuid4 = lambda: next(activation_generator)
        try:
            return original_create_activation(self, *args, **kwargs)
        finally:
            orchestrator_module.uuid4 = original_uuid4

    monkeypatch.setattr(Orchestrator, "_create_branch", _create_branch)
    monkeypatch.setattr(Orchestrator, "_create_activation", _create_activation)
    return branch_generator


class BranchIdView:
    def __init__(self, id_generator: IdGenerator) -> None:
        self.id_generator = id_generator

    def __getitem__(self, index: int) -> str:
        return f"branch-{self.id_generator[index]}"


@pytest.fixture()
def branch_id(branch_id_generator):
    return BranchIdView(branch_id_generator)


@pytest.fixture()
def mock_task_factory():
    def _wrap(fn, *, alias=None):
        mock = Mock(wraps=fn)

        if inspect.iscoroutinefunction(fn):

            @wraps(fn)
            async def wrapped(*args, **kwargs):
                return await mock(*args, **kwargs)

        else:

            @wraps(fn)
            def wrapped(*args, **kwargs):
                return mock(*args, **kwargs)

        wrapped.__signature__ = inspect.signature(fn)
        wrapped_task = task(alias=alias)(wrapped)
        wrapped_task.mock = mock
        return wrapped_task

    return _wrap
