import inspect
from functools import wraps
from unittest.mock import Mock

import pytest

from elan import task


@pytest.fixture()
def mock_task_factory():
    def _wrap(fn):
        mock = Mock(wraps=fn)

        if inspect.iscoroutinefunction(fn):
            @task
            @wraps(fn)
            async def wrapped(*args, **kwargs):
                return await mock(*args, **kwargs)
        else:
            @task
            @wraps(fn)
            def wrapped(*args, **kwargs):
                return mock(*args, **kwargs)

        wrapped.__signature__ = inspect.signature(fn)
        wrapped.mock = mock
        return wrapped

    return _wrap
