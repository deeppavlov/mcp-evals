"""Public type aliases for mcp_evals."""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Any

from mcp_evals.task import Task

type DepsMaker = Callable[[Task[Any, Any]], AbstractAsyncContextManager[object]]
