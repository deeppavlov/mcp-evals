"""Public type aliases for mcp_evals."""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

type DepsLifecycleFactory = Callable[[], AbstractAsyncContextManager[object]]
