"""Task abstraction for evaluation tasks."""

from abc import ABC
from functools import cached_property
from types import TracebackType
from typing import ClassVar, Self

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import Evaluator

from mcp_evals.secrets import TaskSecrets


# TODO make it generic to secrets type
class Task(ABC):
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
    evaluators: tuple[Evaluator["Task", AgentRunResult], ...]

    output_type: type | None = None
    secrets_type: ClassVar[type[TaskSecrets]] = TaskSecrets

    @cached_property
    def secrets(self) -> TaskSecrets:
        """Load and cache secrets from environment."""
        return self.secrets_type()

    async def __aenter__(self) -> Self:
        await self.setup()
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> bool | None:
        await self.teardown()
        return None

    async def setup(self) -> None:
        """Override to perform setup before agent execution."""
        return

    async def teardown(self) -> None:
        """Override to perform cleanup after agent execution."""
        return
