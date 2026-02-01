"""Conversion from mcp_evals Domain/Task to pydantic_evals Dataset/Case."""

from typing import Any

from pydantic_ai.run import AgentRunResult
from pydantic_evals import Case, Dataset

from mcp_evals.domain import Domain
from mcp_evals.task import Task


def domain_to_dataset(domain: Domain) -> Dataset[Task, AgentRunResult[Any]]:
    """Convert mcp_evals Domain to pydantic_evals Dataset.

    Each Task instance becomes a Case with:
    - `name`: `task.name`
    - `inputs`: the `Task` instance itself (evaluators access it via `ctx.inputs`)
    - `evaluators`: `task.evaluators`
    """
    cases = [
        Case(
            name=task.name,
            inputs=task,  # Task instance is the input — evaluators access it via ctx.inputs
            evaluators=task.evaluators,
        )
        for task in domain.tasks()
    ]
    return Dataset(cases=cases)
