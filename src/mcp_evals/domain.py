"""Domain abstraction for evaluation domains."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from contextlib import AsyncExitStack
from functools import cached_property
from types import TracebackType
from typing import TYPE_CHECKING, Any, ClassVar, Self, cast

import anyio
from loguru import logger
from pydantic_ai.mcp import MCPServer
from pydantic_ai.toolsets import CombinedToolset

from mcp_evals.secrets import DomainSecrets

if TYPE_CHECKING:
    from mcp_evals.task import Task


class Domain[SecretsT: DomainSecrets](ABC):
    """Abstract base for evaluation domains.

    Domain is an async context manager that:
    1. Calls setup() for user-defined initialization
    2. Connects to MCP servers
    3. Provides toolset for agent execution
    4. Disconnects MCP servers
    5. Calls teardown() for user-defined cleanup

    Required attributes/methods:
    - `name: str`                    - Unique domain identifier
    - `mcp_servers() -> list`        - Returns MCP server configurations
    - `tasks() -> list[Task]`        - Returns Task instances to evaluate

    Optional attributes:
    - `secrets_type: ClassVar[type]` - BaseSettings subclass for secrets
    - `supports_concurrency: bool`   - If True, tasks within this domain may be evaluated concurrently

    Lifecycle methods (override as needed):
    - `setup()`    - Called before MCP servers are started
    - `teardown()` - Called after MCP servers are stopped

    Note: single instance support a single entry and exit, so multiple
    ``async with domain`` on the same object will raise exception.
    """

    name: str
    supports_concurrency: ClassVar[bool] = False
    _stack: AsyncExitStack[Any] | None = None

    def __init__(self, tool_retries: int = 1) -> None:
        """Init."""
        self.tool_retries = tool_retries
        self._lifecycle_lock = anyio.Lock()

    @abstractmethod
    def mcp_servers(self) -> Sequence[MCPServer]:
        """Return MCP server configurations.

        Note:
            this method should pass `tool_retries` to MCP toolsets (if present)
        """

    @abstractmethod
    def tasks(self) -> Sequence["Task[Any, Any]"]:
        """Return Task instances to evaluate in this domain."""

    secrets_type: ClassVar[type[SecretsT]] = cast("type[SecretsT]", DomainSecrets)

    @cached_property
    def secrets(self) -> SecretsT:
        """Load and cache secrets from environment."""
        return self.secrets_type()

    _toolset: CombinedToolset | None = None

    @property
    def toolset(self) -> CombinedToolset:
        """Access the CombinedToolset. Only available inside context."""
        if self._toolset is None:
            msg = f"Domain '{self.name}' toolset accessed outside context. Use 'async with domain:' first."
            raise RuntimeError(msg)
        return self._toolset

    async def __aenter__(self) -> Self:
        async with self._lifecycle_lock:
            if self._stack is not None:
                msg = f"Attempted entering domain {self.name} twice"
                raise RuntimeError(msg)

            logger.debug(f"[{self.name}] Entering domain...")
            async with AsyncExitStack() as stack:
                await self.setup(stack)
                logger.debug(f"[{self.name}] Connecting to MCP servers...")
                self._toolset = CombinedToolset(self.mcp_servers())
                await stack.enter_async_context(self._toolset)
                self._stack = stack.pop_all()
            logger.success(f"[{self.name}] Entered domain!")
            return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> bool | None:
        async with self._lifecycle_lock:
            if self._stack is None:
                msg = f"Attempted quitting domain {self.name} twice"
                raise RuntimeError(msg)

            logger.debug(f"[{self.name}] Quitting domain...")
            await self._stack.aclose()
            self._stack = None
            logger.success(f"[{self.name}] Quit domain!")
            return None

    async def setup(self, stack: AsyncExitStack[Any]) -> None:  # noqa: ARG002
        """Override to perform setup before agent execution.

        Args:
            stack: exit stack to bind setup and teardown operations

        Note:
            all the setup operations should be added to async exit stack, otherwise
            proper cleanup is not guaranteed
        """
        return
