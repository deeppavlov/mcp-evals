"""Internal runner for executing domains and tasks."""

from typing import Any

from pydantic_ai.agent import Agent
from pydantic_evals.reporting import EvaluationReport

from mcp_evals._internal.conversion import domain_to_dataset
from mcp_evals.domain import Domain
from mcp_evals.types import DepsMaker, EvaluatedFn

from ._base import BaseDomainRunner
from ._utils import task_lifecycle


class DomainRunnerInferenceOnly(BaseDomainRunner):
    def __init__(self, agent: Agent[Any, Any], deps_maker: DepsMaker | None = None) -> None:
        super().__init__(agent=agent, deps_maker=deps_maker)

    async def run_domain(
        self,
        domain: Domain[Any],
        experiment_name: str | None,
        evaluated_fn: EvaluatedFn,
    ) -> EvaluationReport:
        dataset = domain_to_dataset(domain)

        return await dataset.evaluate(
            evaluated_fn,
            max_concurrency=1,  # Sequential by default for stateful tasks
            case_context_manager=task_lifecycle,  # Task context wraps task + evaluators
            progress=False,
            name=experiment_name,
        )
