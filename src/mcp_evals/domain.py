"""Domain abstraction for evaluation domains."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from contextlib import AsyncExitStack
from functools import cached_property
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING, Any, ClassVar, Self, cast

from loguru import logger
from pydantic_ai.mcp import MCPServer
from pydantic_ai.toolsets import CombinedToolset

from mcp_evals.checkpoint import Checkpoint
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
    - `_tasks_impl() -> list[Task]` - Returns all Task instances (subclass implements this)

    Optional attributes:
    - `checkpoint`                   - Checkpoint instance for resumable runs (set from checkpoint_path in __init__)
    - `secrets_type: ClassVar[type]` - BaseSettings subclass for secrets

    Lifecycle methods (override as needed):
    - `setup()`    - Called before MCP servers are started
    """

    name: str
    _stack: AsyncExitStack[Any] | None = None

    def __init__(
        self,
        tool_retries: int = 1,
        *,
        checkpoint_path: Path | str | None = None,
    ) -> None:
        """Init.

        Args:
            tool_retries: Retry count for MCP tool calls.
            checkpoint_path: If set, enables checkpointing for resumable runs;
                finished (scope, task) keys are stored in this file.
        """
        self.tool_retries = tool_retries
        self.checkpoint: Checkpoint | None = Checkpoint(Path(checkpoint_path)) if checkpoint_path is not None else None

    @abstractmethod
    def mcp_servers(self) -> Sequence[MCPServer]:
        """Return MCP server configurations.

        Note:
            this method should pass `tool_retries` to MCP toolsets (if present)
        """

    @abstractmethod
    def _tasks_impl(self) -> Sequence["Task[Any, Any]"]:
        """Return all Task instances to evaluate in this domain.

        Subclasses implement this; filtering by checkpoint (when enabled) is
        applied by tasks(scope=...).
        """

    def tasks(self, scope: str | None = "default") -> Sequence["Task[Any, Any]"]:
        r"""Return tasks for the given scope, excluding already-finished when checkpoint is set.

        Args:
            scope: When None, return all tasks (no checkpoint filtering). Used by
                CV/HoldOut runners that filter per phase themselves. When
                "default", return tasks not yet finished for the default scope
                (used by inference-only and self-correction).

        Returns:
            Task list, optionally filtered by checkpoint.
        """
        all_tasks = self._tasks_impl()
        if scope is None or self.checkpoint is None:
            return all_tasks
        return [t for t in all_tasks if not self.checkpoint.is_finished(scope, t.name)]

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
        if self._stack is not None:
            msg = f"Attempted entering domain {self.name} twice"
            raise RuntimeError(msg)

        logger.debug(f"[{self.name}] Entering domain...")
        if self.checkpoint is not None:
            self.checkpoint.load()
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
