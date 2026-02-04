"""Benchmark runner for executing evaluation benchmarks."""

from typing import Any

from pydantic_ai.agent import Agent
from pydantic_evals.reporting import EvaluationReport

from mcp_evals._internal.runner import run_domain
from mcp_evals.domain import Domain


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

    async def run(self) -> list[EvaluationReport]:
        """Run all tasks from all domains.

        Returns:
            Evaluation reports for all domains
        """
        eval_reports: list[EvaluationReport] = []

        for domain in self.domains:
            eval_report = await run_domain(domain, self.agent)
            eval_reports.append(eval_report)

        return eval_reports
