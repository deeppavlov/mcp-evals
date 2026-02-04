"""Domain abstraction for evaluation domains."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from functools import cached_property
from types import TracebackType
from typing import TYPE_CHECKING, Any, ClassVar, Self, cast

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

    Lifecycle methods (override as needed):
    - `setup()`    - Called before MCP servers are started
    - `teardown()` - Called after MCP servers are stopped
    """

    name: str

    @abstractmethod
    def mcp_servers(self) -> Sequence[MCPServer]:
        """Return MCP server configurations."""

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
        # Prevent re-entry
        if self._toolset is not None:
            msg = f"Domain '{self.name}' context already entered"
            logger.exception(msg)
            raise RuntimeError(msg)

        logger.debug(f"[{self.name}] Entering domain")

        await self.setup()

        logger.debug(f"[{self.name}] Connecting to MCP servers...")
        self._toolset = CombinedToolset(self.mcp_servers())
        await self._toolset.__aenter__()

        logger.success(f"[{self.name}] Entered domain!")

        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> bool | None:
        if self._toolset is not None:
            logger.debug(f"[{self.name}] Disconnecting MCP servers...")
            await self._toolset.__aexit__(exc_type, exc_val, exc_tb)
            self._toolset = None

        logger.debug(f"[{self.name}] Quitting domain...")
        await self.teardown()

        logger.success(f"[{self.name}] Quit domain!")

        return None

    async def setup(self) -> None:
        """Override to perform setup before MCP servers are started."""
        return

    async def teardown(self) -> None:
        """Override to perform cleanup after MCP servers are stopped."""
        return
