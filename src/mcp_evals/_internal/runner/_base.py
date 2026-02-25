"""Internal runner for executing domains and tasks."""

from abc import ABC, abstractmethod
from functools import partial
from typing import Any

from pydantic_ai.agent import Agent
from pydantic_evals.reporting import EvaluationReport

from mcp_evals._internal.evaluated_fn import run_agent_on_task
from mcp_evals.domain import Domain
from mcp_evals.types import DepsMaker, EvaluatedFn, RunResultProcessor

from ._utils import default_deps_maker


class BaseDomainRunner(ABC):
    def __init__(
        self,
        agent: Agent[Any, Any],
        deps_maker: DepsMaker | None = None,
        max_tasks: int | None = None,
        run_result_processor: RunResultProcessor | None = None,
    ) -> None:
        self.agent = agent
        self.deps_maker = deps_maker
        self.max_tasks = max_tasks
        self.run_result_processor = run_result_processor

    async def run(self, domain: Domain[Any], experiment_name: str | None = None) -> EvaluationReport:
        deps_maker = self.deps_maker or default_deps_maker()

        async with domain:
            evaluated_fn = partial(
                run_agent_on_task,
                agent=self.agent,
                toolset=domain.toolset,
                deps_maker=deps_maker,
                run_result_processor=self.run_result_processor,
            )
            return await self.run_domain(domain=domain, experiment_name=experiment_name, evaluated_fn=evaluated_fn)

    @abstractmethod
    async def run_domain(
        self,
        domain: Domain[Any],
        experiment_name: str | None,
        evaluated_fn: EvaluatedFn,
    ) -> EvaluationReport: ...
