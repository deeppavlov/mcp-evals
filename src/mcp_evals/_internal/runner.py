"""Internal runner for executing domains and tasks."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import partial
from typing import Any

from pydantic_ai.agent import Agent
from pydantic_ai.run import AgentRunResult
from pydantic_evals import Case
from pydantic_evals.reporting import EvaluationReport

from mcp_evals._internal.conversion import domain_to_dataset
from mcp_evals._internal.evaluated_fn import run_agent_on_task
from mcp_evals.domain import Domain
from mcp_evals.task import Task


@asynccontextmanager
async def task_lifecycle(case: Case[Task[Any, Any], AgentRunResult, None]) -> AsyncIterator[None]:
    """Context manager that wraps task execution + evaluation.

    This ensures the task context (setup/teardown) spans both:
    - Task execution (agent.run)
    - Evaluator execution (evaluator.evaluate)

    This is critical because evaluators often need to check the environment
    state (files, database, etc.) that was set up during task.setup(), and
    this state must remain available until after evaluators complete.
    """
    task = case.inputs  # In mcp_evals, inputs IS the Task instance
    async with task:
        yield


async def run_domain(domain: Domain[Any], agent: Agent[Any, Any]) -> EvaluationReport:
    """Run all tasks in a domain.

    Domain is an async context manager that manages CombinedToolset lifecycle
    and custom user's setup/teardown logic.
    """
    async with domain:
        dataset = domain_to_dataset(domain)

        evaluated_fn = partial(
            run_agent_on_task,
            agent=agent,
            toolset=domain.toolset,
        )

        return await dataset.evaluate(
            evaluated_fn,
            max_concurrency=1,  # Sequential by default for stateful tasks
            case_context_manager=task_lifecycle,  # Task context wraps task + evaluators
            progress=False,
        )
