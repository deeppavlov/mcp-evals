"""Benchmark runner for executing evaluation benchmarks."""

from typing import Any

from pydantic_ai.agent import Agent
from pydantic_ai.usage import UsageLimits
from pydantic_evals.reporting import EvaluationReport

from ._internal.runner import DomainRunner, Grouper, PlainGrouper
from .domain import Domain
from .types import DepsMaker, RunResultProcessor, TrainingTestingCallback


class BenchmarkRunner:
    """Runner for executing evaluation benchmarks across multiple domains."""

    def __init__(  # noqa: PLR0913
        self,
        agent: Agent[Any, Any],
        domains: list[Domain[Any]],
        grouper: Grouper | None = None,
        deps_maker: DepsMaker | None = None,
        experiment_name: str | None = None,
        max_tasks: int | None = None,
        use_self_correction: bool = False,
        max_self_correction_retries: int = 3,
        start_training: TrainingTestingCallback | None = None,
        start_testing: TrainingTestingCallback | None = None,
        run_result_processor: RunResultProcessor | None = None,
        usage_limits: UsageLimits | None = None,
    ) -> None:
        """Initialize the benchmark runner.

        Args:
            agent: The agent to evaluate.
            domains: Domains to run (each yields tasks).
            grouper: Grouper instance that produces train/test splittings
                (e.g. PlainGrouper(), HoldOutGrouper(test_ratio=0.2), CVGrouper(n_splits=5)).
            deps_maker: Optional callable that takes the task instance and returns
                an async context manager yielding deps for that task.
            experiment_name: Optional experiment name for reporting.
            max_tasks: Optional cap on number of tasks per domain.
            use_self_correction: If True, use self-correction evaluated function
                (agent sees evaluator feedback and can retry).
            max_self_correction_retries: Max retries when use_self_correction is True.
            start_training: Optional callback invoked before each training phase.
            start_testing: Optional callback invoked before each testing phase.
            run_result_processor: Optional callback invoked after each agent run.
            usage_limits: Optional usage limits for the agent.
        """
        self.agent = agent
        self.domains = domains
        self.grouper = grouper or PlainGrouper()
        self.deps_maker = deps_maker
        self.experiment_name = experiment_name
        self.max_tasks = max_tasks
        self.use_self_correction = use_self_correction
        self.max_self_correction_retries = max_self_correction_retries
        self.start_training = start_training
        self.start_testing = start_testing
        self.run_result_processor = run_result_processor
        self.usage_limits = usage_limits

    async def run(self) -> list[EvaluationReport]:
        """Run all tasks from all domains.

        Returns:
            Evaluation reports for all domains.
        """
        runner = DomainRunner(
            agent=self.agent,
            grouper=self.grouper,
            deps_maker=self.deps_maker,
            max_tasks=self.max_tasks,
            use_self_correction=self.use_self_correction,
            max_self_correction_retries=self.max_self_correction_retries,
            start_training=self.start_training,
            start_testing=self.start_testing,
            run_result_processor=self.run_result_processor,
            usage_limits=self.usage_limits,
        )
        return [await runner.run(domain, experiment_name=self.experiment_name) for domain in self.domains]
