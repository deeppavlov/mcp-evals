"""Task abstraction for evaluation tasks."""

from abc import ABC
from collections.abc import Sequence
from contextlib import AsyncExitStack
from functools import cached_property
from importlib.resources import files
from types import TracebackType
from typing import TYPE_CHECKING, Any, ClassVar, Generic, Self, TypeVar

from loguru import logger
from pydantic_ai.mcp import MCPServer
from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import Evaluator

from mcp_evals.secrets import TaskSecrets

# workaround for python 3.12, because it doesnt support `default` value for type var
if TYPE_CHECKING:
    SecretsT = TypeVar("SecretsT", bound=TaskSecrets, default=TaskSecrets)
    OutputT = TypeVar("OutputT", default=str)
else:
    SecretsT = TypeVar("SecretsT", bound=TaskSecrets)
    OutputT = TypeVar("OutputT")


class Task(ABC, Generic[SecretsT, OutputT]):  # noqa: UP046
    """Abstract base for evaluation tasks.

    Required attributes (class attributes or @property):
    - `name: str`                       - Unique task identifier
    - `goal: str`                       - Prompt/instruction for the agent
    - `evaluators: tuple[Evaluator]`    - Verification functions

    Optional attributes:
    - `output_type: type | None`        - Pydantic model for structured output
    - `secrets_type: ClassVar[type]`    - BaseSettings subclass for secrets

    Lifecycle methods (override as needed):
    - `setup()`                         - Called before agent runs
    - `teardown()`                      - Called after evaluation completes
    """

    name: str
    goal: str
    evaluators: tuple[Evaluator[Self, AgentRunResult], ...]

    output_type: ClassVar[type[OutputT]]
    secrets_type: ClassVar[type[SecretsT]]

    _stack: AsyncExitStack[Any] | None = None

    def mcp_servers(self) -> Sequence[MCPServer]:
        """Return task-specific MCP server."""
        return []

    @cached_property
    def secrets(self) -> SecretsT:
        """Load and cache secrets from environment."""
        return self.secrets_type()

    async def __aenter__(self) -> Self:
        if self._stack is not None:
            msg = f"Attempted entering task {self.name} twice"
            raise RuntimeError(msg)

        logger.debug(f"[{self.name}] Entering task...")
        async with AsyncExitStack() as stack:
            await self.setup(stack)
            self._stack = stack.pop_all()
        logger.success(f"[{self.name}] Entered task!")
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> bool | None:
        if self._stack is None:
            msg = f"Attempted quitting task {self.name} twice"
            raise RuntimeError(msg)

        logger.debug(f"[{self.name}] Quitting task...")
        await self._stack.aclose()
        self._stack = None
        logger.success(f"[{self.name}] Quit task!")
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


class GoalFromDescriptionMixin:
    """Mixin that provides goal by loading description.md from the task's package.

    Requires the concrete class to have __module__ set to the package that contains
    description.md (same directory as the task module). Optional fallback: set
    _goal on the class if description.md is missing.
    """

    @property
    def goal(self) -> str:
        """Load goal from description.md."""
        try:
            return files(self.__class__.__module__).joinpath("description.md").read_text(encoding="utf-8")
        except FileNotFoundError:
            return getattr(self.__class__, "_goal", "") or ""
