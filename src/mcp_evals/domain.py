"""Domain abstraction for evaluation domains."""

from abc import ABC, abstractmethod
from functools import cached_property
from types import TracebackType
from typing import TYPE_CHECKING, ClassVar, Self

from pydantic_ai.mcp import MCPServer
from pydantic_ai.toolsets import CombinedToolset

from mcp_evals.secrets import DomainSecrets

if TYPE_CHECKING:
    from mcp_evals.task import Task


class Domain(ABC):
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
    def mcp_servers(self) -> list[MCPServer]:
        """Return MCP server configurations."""

    @abstractmethod
    def tasks(self) -> list["Task"]:
        """Return Task instances to evaluate in this domain."""

    secrets_type: ClassVar[type[DomainSecrets]] = DomainSecrets

    @cached_property
    def secrets(self) -> DomainSecrets:
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
            raise RuntimeError(msg)

        await self.setup()

        self._toolset = CombinedToolset(self.mcp_servers())
        await self._toolset.__aenter__()

        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> bool | None:
        if self._toolset is not None:
            await self._toolset.__aexit__(exc_type, exc_val, exc_tb)
            self._toolset = None

        await self.teardown()

        return None

    async def setup(self) -> None:
        """Override to perform setup before MCP servers are started."""
        return

    async def teardown(self) -> None:
        """Override to perform cleanup after MCP servers are stopped."""
        return
