"""Task abstraction for evaluation tasks."""

from abc import ABC
from functools import cached_property
from types import TracebackType
from typing import TYPE_CHECKING, ClassVar, Generic, Self, TypeVar

from loguru import logger
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

    @cached_property
    def secrets(self) -> SecretsT:
        """Load and cache secrets from environment."""
        return self.secrets_type()

    async def __aenter__(self) -> Self:
        logger.debug(f"[{self.name}] Entering task...")
        await self.setup()
        logger.success(f"[{self.name}] Entered task!")
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> bool | None:
        logger.debug(f"[{self.name}] Quitting task...")
        await self.teardown()
        logger.success(f"[{self.name}] Quit task!")
        return None

    async def setup(self) -> None:
        """Override to perform setup before agent execution."""
        return

    async def teardown(self) -> None:
        """Override to perform cleanup after agent execution."""
        return
