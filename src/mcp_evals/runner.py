"""Benchmark runner for executing evaluation benchmarks."""

from typing import Any

from pydantic_ai.agent import Agent
from pydantic_evals.reporting import EvaluationReport

from mcp_evals._internal.runner import BaseDomainRunner, DomainRunnerInferenceOnly
from mcp_evals.domain import Domain
from mcp_evals.types import DepsMaker, Runner


class BenchmarkRunner:
    """Runner for executing evaluation benchmarks across multiple domains."""

    def __init__(
        self,
        agent: Agent[Any, Any],
        domains: list[Domain[Any]],
        runner: Runner,
        deps_maker: DepsMaker | None = None,
        experiment_name: str | None = None,
    ) -> None:
        """Initialize the benchmark runner."""
        self.agent = agent
        self.domains = domains
        self.runner = runner
        self.deps_maker = deps_maker
        self.experiment_name = experiment_name

    async def run(self) -> list[EvaluationReport]:
        """Run all tasks from all domains.

        Args:
            deps_maker: Optional callable that takes the task instance and returns
                an async context manager yielding deps for that task. When omitted,
                a default maker that yields None is used (no custom deps). Pass a
                custom factory to provide fresh deps per task (e.g. DB connection,
                request-scoped state).
            experiment_name: Optional experiment name for reporting.

        Returns:
            Evaluation reports for all domains
        """
        runner = self._create_runner()
        return [await runner.run(domain, experiment_name=self.experiment_name) for domain in self.domains]

    def _create_runner(self) -> BaseDomainRunner:
        if self.runner == Runner.INFERENCE_ONLY:
            return DomainRunnerInferenceOnly(agent=self.agent, deps_maker=self.deps_maker)
        if self.runner == Runner.HOLD_OUT:
            raise NotImplementedError("HO is not implemented for now")
        if self.runner == Runner.CROSS_VALIDATION:
            raise NotImplementedError("CV is not implemented for now")
        raise ValueError("Invalid runner")
