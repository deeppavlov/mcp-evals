"""Cross-validation domain runner: K-fold, run train then test per fold, merge test reports."""

from typing import Any

from pydantic_ai.agent import Agent
from pydantic_ai.usage import UsageLimits
from pydantic_evals.reporting import EvaluationReport

from mcp_evals._internal.conversion import tasks_to_dataset
from mcp_evals.domain import Domain
from mcp_evals.types import DepsMaker, EvaluatedFn, RunResultProcessor, TrainingTestingCallback

from ._base import BaseDomainRunner
from ._splits import k_fold_split
from ._utils import task_lifecycle


def _filter_by_checkpoint(
    domain: Domain[Any],
    scope: str,
    tasks: list[Any],
    indices: list[int],
) -> list[Any]:
    """Return task subset for indices, excluding those already finished for scope."""
    subset = [tasks[i] for i in indices]
    if domain.checkpoint is None:
        return subset
    return [t for t in subset if not domain.checkpoint.is_finished(scope, t.name)]


async def _run_fold_train(
    domain: Domain[Any],
    fold_idx: int,
    tasks: list[Any],
    train_indices: list[int],
    evaluated_fn: EvaluatedFn,
    experiment_name: str | None,
) -> None:
    """Run training phase for one fold."""
    train_tasks = _filter_by_checkpoint(domain, f"fold_{fold_idx}_train", tasks, train_indices)
    if not train_tasks:
        return
    await tasks_to_dataset(train_tasks).evaluate(
        evaluated_fn,
        max_concurrency=1,
        case_context_manager=task_lifecycle(domain, scope=f"fold_{fold_idx}_train"),
        progress=False,
        name=f"{experiment_name or 'cv'}_train_{fold_idx}_",
    )


async def _run_fold_test(
    domain: Domain[Any],
    fold_idx: int,
    tasks: list[Any],
    test_indices: list[int],
    evaluated_fn: EvaluatedFn,
    experiment_name: str | None,
) -> EvaluationReport | None:
    """Run test phase for one fold; return report if there were test tasks."""
    test_tasks = _filter_by_checkpoint(domain, f"fold_{fold_idx}_test", tasks, test_indices)
    if not test_tasks:
        return None
    return await tasks_to_dataset(test_tasks).evaluate(
        evaluated_fn,
        max_concurrency=1,
        case_context_manager=task_lifecycle(domain, scope=f"fold_{fold_idx}_test"),
        progress=False,
        name=f"{experiment_name or 'cv'}_test_{fold_idx}" if experiment_name else None,
    )


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
        usage_limits: UsageLimits | None = None,
    ) -> None:
        super().__init__(
            agent=agent,
            deps_maker=deps_maker,
            max_tasks=max_tasks,
            run_result_processor=run_result_processor,
            usage_limits=usage_limits,
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
        tasks = list(domain.tasks(scope=None))
        if self.max_tasks is not None:
            tasks = tasks[: self.max_tasks]
        fold_reports: list[EvaluationReport] = []

        for fold_idx, (train_indices, test_indices) in enumerate(
            k_fold_split(len(tasks), self.n_splits, self.random_state)
        ):
            if self.start_training is not None:
                await self.start_training()

            if train_indices:
                await _run_fold_train(
                    domain,
                    fold_idx,
                    tasks,
                    train_indices,
                    evaluated_fn,
                    experiment_name,
                )

            if self.start_testing is not None:
                await self.start_testing()

            if test_indices:
                report = await _run_fold_test(
                    domain,
                    fold_idx,
                    tasks,
                    test_indices,
                    evaluated_fn,
                    experiment_name,
                )
                if report is not None:
                    fold_reports.append(report)

        combined_cases = []
        for report in fold_reports:
            combined_cases.extend(report.cases)

        return EvaluationReport(
            name=experiment_name or "cross_validation",
            cases=combined_cases,
        )
