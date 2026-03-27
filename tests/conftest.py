import inspect
import importlib
from functools import wraps
from unittest.mock import Mock

import pytest

from elan import task

task_module = importlib.import_module("elan.task")


@pytest.fixture(autouse=True)
def clear_task_registry():
    task_module._TASKS_BY_KEY.clear()
    task_module._TASKS_BY_ALIAS.clear()
    yield
    task_module._TASKS_BY_KEY.clear()
    task_module._TASKS_BY_ALIAS.clear()


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
