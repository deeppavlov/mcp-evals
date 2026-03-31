"""Internal runner for executing domains and tasks."""

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any, Literal

from loguru import logger
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.run import AgentRunResult
from pydantic_evals import Case
from pydantic_evals.lifecycle import CaseLifecycle
from pydantic_evals.reporting import ReportCase, ReportCaseFailure

from mcp_evals.task import Task
from mcp_evals.types import DepsMaker

from ._run_state import RunState

Phase = Literal["train", "test"]


@asynccontextmanager
async def _no_deps_cm() -> AsyncIterator[None]:
    yield None


def default_deps_maker() -> DepsMaker:
    """Default deps maker used when user does not pass one (yields None)."""
    return lambda _task: _no_deps_cm()


def _failure_is_usage_limit(result: ReportCaseFailure[Any, Any, Any]) -> bool:
    """Detect usage-limit failures when only string error fields are available."""
    name = UsageLimitExceeded.__name__
    return name in result.error_message or name in result.error_stacktrace


def make_task_lifecycle(
    state: RunState,
    split_idx: int,
    phase: Phase,
) -> type[CaseLifecycle[Task[Any, Any], AgentRunResult[Any], None]]:
    """Return a ``CaseLifecycle`` subclass for ``Dataset.evaluate(..., lifecycle=...)``.

    Enters the task async context in ``setup()`` (via :class:`~contextlib.AsyncExitStack`)
    so it stays active through the evaluated function and evaluators; ``teardown()``
    closes the stack and updates run state.

    Marks the task finished in run state on success, or on usage-limit exhaustion
    (retrying the same task would not help). Other failures do not mark finished
    so resume can retry the task.
    """

    class McpTaskLifecycle(CaseLifecycle[Task[Any, Any], AgentRunResult[Any], None]):
        def __init__(self, case: Case[Task[Any, Any], AgentRunResult[Any], None]) -> None:
            super().__init__(case)
            self._exit_stack: AsyncExitStack | None = None

        async def setup(self) -> None:
            self._exit_stack = AsyncExitStack()
            task = self.case.inputs
            await self._exit_stack.enter_async_context(task)

        async def teardown(
            self,
            result: ReportCase[Task[Any, Any], AgentRunResult[Any], None]
            | ReportCaseFailure[Task[Any, Any], AgentRunResult[Any], None],
        ) -> None:
            if self._exit_stack is not None:
                await self._exit_stack.aclose()
                self._exit_stack = None

            task = self.case.inputs
            if isinstance(result, ReportCase):
                await state.mark_task_finished(split_idx, phase, task.name)
                return

            if _failure_is_usage_limit(result):
                logger.exception(
                    f"[{task.name}] Usage exceeded. "
                    "Task will be marked as finished (not retried), but case marked as failed in reporting."
                )
                await state.mark_task_finished(split_idx, phase, task.name)

    return McpTaskLifecycle
