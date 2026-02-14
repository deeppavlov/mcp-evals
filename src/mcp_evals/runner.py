"""Benchmark runner for executing evaluation benchmarks."""

from typing import Any

from pydantic_ai.agent import Agent
from pydantic_evals.reporting import EvaluationReport

from mcp_evals._internal.runner import run_domain
from mcp_evals.domain import Domain
from mcp_evals.types import DepsLifecycleFactory


class BenchmarkRunner:
    """Runner for executing evaluation benchmarks across multiple domains."""

    def __init__(
        self,
        agent: Agent[Any, Any],
        domains: list[Domain[Any]],
    ) -> None:
        """Initialize the benchmark runner.

        Args:
            agent: The pydantic_ai Agent to use for task execution
            domains: List of Domain instances to evaluate
        """
        self.agent = agent
        self.domains = domains

    async def run(
        self,
        deps_lifecycle: DepsLifecycleFactory | None = None,
        experiment_name: str | None = None,
    ) -> list[EvaluationReport]:
        """Run all tasks from all domains.

        Args:
            deps_lifecycle: Optional callable that returns an async context manager
                yielding deps for each task. When omitted, a default lifecycle that
                yields None is used (no custom deps). Pass a custom factory to
                provide fresh deps per task (e.g. DB connection, request-scoped state).
            experiment_name: Optional experiment name for reporting.

        Returns:
            Evaluation reports for all domains
        """
        eval_reports: list[EvaluationReport] = []

        for domain in self.domains:
            eval_report = await run_domain(
                domain,
                self.agent,
                experiment_name=experiment_name,
                deps_lifecycle=deps_lifecycle,
            )
            eval_reports.append(eval_report)

        return eval_reports
