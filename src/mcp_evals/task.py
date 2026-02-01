"""Task abstraction for evaluation tasks."""

from abc import ABC
from collections.abc import Sequence
from contextlib import AbstractAsyncContextManager
from functools import cached_property
from types import TracebackType
from typing import TYPE_CHECKING, ClassVar, Self

from mcp_evals.secrets import TaskSecrets

if TYPE_CHECKING:
    from pydantic_evals.evaluators import Evaluator


class Task(AbstractAsyncContextManager, ABC):
    """Abstract base for evaluation tasks.

    Required attributes (class attributes or @property):
    - `name: str`                       - Unique task identifier
    - `goal: str`                       - Prompt/instruction for the agent
    - `evaluators: Sequence[Evaluator]` - Verification functions

    Optional attributes:
    - `output_type: type | None`        - Pydantic model for structured output
    - `secrets_type: ClassVar[type]`    - BaseSettings subclass for secrets

    Lifecycle methods (override as needed):
    - `setup()`                         - Called before agent runs
    - `teardown()`                      - Called after evaluation completes
    """

    name: str
    goal: str
    evaluators: Sequence["Evaluator"]

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

    async def teardown(self) -> None:
        """Override to perform cleanup after agent execution."""
