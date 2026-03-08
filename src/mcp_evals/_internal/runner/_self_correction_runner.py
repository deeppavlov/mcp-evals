"""Internal runner for self-correction: agent sees evaluation feedback and can retry."""

from functools import partial
from typing import Any

from pydantic_ai.agent import Agent
from pydantic_ai.usage import UsageLimits
from pydantic_evals.reporting import EvaluationReport

from mcp_evals._internal.conversion import domain_to_dataset
from mcp_evals._internal.evaluated_fn import run_agent_on_task_with_self_correction
from mcp_evals.domain import Domain
from mcp_evals.types import DepsMaker, EvaluatedFn, RunResultProcessor

from ._base import BaseDomainRunner
from ._utils import default_deps_maker, task_lifecycle


class DomainRunnerSelfCorrection(BaseDomainRunner):
    """Runner that lets the agent see evaluator feedback and retry with fixes."""

    def __init__(
        self,
        agent: Agent[Any, Any],
        deps_maker: DepsMaker | None = None,
        max_tasks: int | None = None,
        run_result_processor: RunResultProcessor | None = None,
        usage_limits: UsageLimits | None = None,
        max_self_correction_retries: int = 3,
    ) -> None:
        super().__init__(
            agent=agent,
            deps_maker=deps_maker,
            max_tasks=max_tasks,
            run_result_processor=run_result_processor,
            usage_limits=usage_limits,
        )
        self.max_self_correction_retries = max_self_correction_retries

    async def run_domain(
        self,
        domain: Domain[Any],
        experiment_name: str | None,
        evaluated_fn: EvaluatedFn,
    ) -> EvaluationReport:
        deps_maker = self.deps_maker or default_deps_maker()
        evaluated_fn = partial(
            run_agent_on_task_with_self_correction,
            agent=self.agent,
            toolset=domain.toolset,
            deps_maker=deps_maker,
            run_result_processor=self.run_result_processor,
            usage_limits=self.usage_limits,
            max_retries=self.max_self_correction_retries,
        )
        dataset = domain_to_dataset(domain, max_tasks=self.max_tasks)
        return await dataset.evaluate(
            evaluated_fn,
            max_concurrency=1,
            case_context_manager=task_lifecycle(domain, scope="default"),
            progress=False,
            name=experiment_name,
        )
