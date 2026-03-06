"""Benchmark runner for executing evaluation benchmarks."""

from typing import Any

from pydantic_ai.agent import Agent
from pydantic_ai.usage import UsageLimits
from pydantic_evals.reporting import EvaluationReport

from mcp_evals._internal.runner import (
    BaseDomainRunner,
    DomainRunnerCrossValidation,
    DomainRunnerHoldOut,
    DomainRunnerInferenceOnly,
    DomainRunnerSelfCorrection,
)
from mcp_evals.domain import Domain
from mcp_evals.types import DepsMaker, Runner, RunResultProcessor, TrainingTestingCallback


class BenchmarkRunner:
    """Runner for executing evaluation benchmarks across multiple domains."""

    def __init__(  # noqa: PLR0913
        self,
        agent: Agent[Any, Any],
        domains: list[Domain[Any]],
        runner: Runner,
        deps_maker: DepsMaker | None = None,
        experiment_name: str | None = None,
        max_tasks: int | None = None,
        max_self_correction_retries: int = 3,
        hold_out_test_ratio: float = 0.2,
        cv_n_splits: int = 5,
        random_state: int | None = None,
        start_training: TrainingTestingCallback | None = None,
        start_testing: TrainingTestingCallback | None = None,
        run_result_processor: RunResultProcessor | None = None,
        usage_limits: UsageLimits | None = None,
    ) -> None:
        """Initialize the benchmark runner."""
        self.agent = agent
        self.domains = domains
        self.runner = runner
        self.deps_maker = deps_maker
        self.experiment_name = experiment_name
        self.max_tasks = max_tasks
        self.max_self_correction_retries = max_self_correction_retries
        self.hold_out_test_ratio = hold_out_test_ratio
        self.cv_n_splits = cv_n_splits
        self.random_state = random_state
        self.start_training = start_training
        self.start_testing = start_testing
        self.run_result_processor = run_result_processor
        self.usage_limits = usage_limits

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
            return DomainRunnerInferenceOnly(
                agent=self.agent,
                deps_maker=self.deps_maker,
                max_tasks=self.max_tasks,
                run_result_processor=self.run_result_processor,
                usage_limits=self.usage_limits,
            )
        if self.runner == Runner.HOLD_OUT:
            return DomainRunnerHoldOut(
                agent=self.agent,
                deps_maker=self.deps_maker,
                max_tasks=self.max_tasks,
                test_ratio=self.hold_out_test_ratio,
                random_state=self.random_state,
                start_training=self.start_training,
                start_testing=self.start_testing,
                run_result_processor=self.run_result_processor,
                usage_limits=self.usage_limits,
            )
        if self.runner == Runner.CROSS_VALIDATION:
            return DomainRunnerCrossValidation(
                agent=self.agent,
                deps_maker=self.deps_maker,
                max_tasks=self.max_tasks,
                n_splits=self.cv_n_splits,
                random_state=self.random_state,
                start_training=self.start_training,
                start_testing=self.start_testing,
                run_result_processor=self.run_result_processor,
                usage_limits=self.usage_limits,
            )
        if self.runner == Runner.SELF_CORRECTION:
            return DomainRunnerSelfCorrection(
                agent=self.agent,
                deps_maker=self.deps_maker,
                max_tasks=self.max_tasks,
                run_result_processor=self.run_result_processor,
                usage_limits=self.usage_limits,
                max_self_correction_retries=self.max_self_correction_retries,
            )
        raise ValueError("Invalid runner")
