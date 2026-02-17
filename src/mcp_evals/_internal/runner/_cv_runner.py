"""Cross-validation domain runner: K-fold, run train then test per fold, merge test reports."""

from typing import Any

from pydantic_ai.agent import Agent
from pydantic_evals.reporting import EvaluationReport

from mcp_evals._internal.conversion import tasks_to_dataset
from mcp_evals.domain import Domain
from mcp_evals.types import DepsMaker, EvaluatedFn, RunResultProcessor, TrainingTestingCallback

from ._base import BaseDomainRunner
from ._splits import k_fold_split
from ._utils import task_lifecycle


class DomainRunnerCrossValidation(BaseDomainRunner):
    """Runner that runs K-fold CV: per fold run train then test, merge test reports."""

    def __init__(
        self,
        agent: Agent[Any, Any],
        deps_maker: DepsMaker | None = None,
        *,
        max_tasks: int | None = None,
        n_splits: int = 5,
        random_state: int | None = None,
        start_training: TrainingTestingCallback | None = None,
        start_testing: TrainingTestingCallback | None = None,
        run_result_processor: RunResultProcessor | None = None,
    ) -> None:
        super().__init__(
            agent=agent,
            deps_maker=deps_maker,
            max_tasks=max_tasks,
            run_result_processor=run_result_processor,
        )
        self.n_splits = n_splits
        self.random_state = random_state
        self.start_training = start_training
        self.start_testing = start_testing

    async def run_domain(
        self,
        domain: Domain[Any],
        experiment_name: str | None,
        evaluated_fn: EvaluatedFn,
    ) -> EvaluationReport:
        tasks = list(domain.tasks())
        if self.max_tasks is not None:
            tasks = tasks[: self.max_tasks]
        fold_reports: list[EvaluationReport] = []

        for fold_idx, (train_indices, test_indices) in enumerate(
            k_fold_split(len(tasks), self.n_splits, self.random_state)
        ):
            if self.start_training is not None:
                await self.start_training()

            if train_indices:
                train_tasks = [tasks[i] for i in train_indices]
                train_dataset = tasks_to_dataset(train_tasks)
                await train_dataset.evaluate(
                    evaluated_fn,
                    max_concurrency=1,
                    case_context_manager=task_lifecycle,
                    progress=False,
                    name=f"{experiment_name or 'cv'}_train_{fold_idx}_",
                )

            if self.start_testing is not None:
                await self.start_testing()

            if test_indices:
                test_tasks = [tasks[i] for i in test_indices]
                test_dataset = tasks_to_dataset(test_tasks)
                report = await test_dataset.evaluate(
                    evaluated_fn,
                    max_concurrency=1,
                    case_context_manager=task_lifecycle,
                    progress=False,
                    name=f"{experiment_name or 'cv'}_test_{fold_idx}" if experiment_name else None,
                )
                fold_reports.append(report)

        combined_cases = []
        for report in fold_reports:
            combined_cases.extend(report.cases)

        return EvaluationReport(
            name=experiment_name or "cross_validation",
            cases=combined_cases,
        )
