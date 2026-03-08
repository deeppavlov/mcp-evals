"""Hold-out domain runner: train/test split, run on train then test, return test report."""

from typing import Any

from pydantic_ai.agent import Agent
from pydantic_ai.usage import UsageLimits
from pydantic_evals.reporting import EvaluationReport

from mcp_evals._internal.conversion import tasks_to_dataset
from mcp_evals.domain import Domain
from mcp_evals.types import DepsMaker, EvaluatedFn, RunResultProcessor, TrainingTestingCallback

from ._base import BaseDomainRunner
from ._splits import hold_out_split
from ._utils import task_lifecycle


class DomainRunnerHoldOut(BaseDomainRunner):
    """Runner that splits tasks into train/test, runs agent on both, returns test report."""

    def __init__(
        self,
        agent: Agent[Any, Any],
        deps_maker: DepsMaker | None = None,
        *,
        max_tasks: int | None = None,
        test_ratio: float = 0.2,
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
        self.test_ratio = test_ratio
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
        train_indices, test_indices = hold_out_split(len(tasks), self.test_ratio, self.random_state)

        if self.start_training is not None:
            await self.start_training()

        if train_indices:
            train_tasks = [tasks[i] for i in train_indices]
            if domain.checkpoint is not None:
                train_tasks = [t for t in train_tasks if not domain.checkpoint.is_finished("train", t.name)]
            if train_tasks:
                train_dataset = tasks_to_dataset(train_tasks)
                await train_dataset.evaluate(
                    evaluated_fn,
                    max_concurrency=1,
                    case_context_manager=task_lifecycle(domain, scope="train"),
                    progress=False,
                    name=f"{experiment_name or 'ho'}_train",
                )

        if self.start_testing is not None:
            await self.start_testing()

        if not test_indices:
            return EvaluationReport(name=experiment_name or "hold_out", cases=[])

        test_tasks = [tasks[i] for i in test_indices]
        if domain.checkpoint is not None:
            test_tasks = [t for t in test_tasks if not domain.checkpoint.is_finished("test", t.name)]
        if not test_tasks:
            return EvaluationReport(name=experiment_name or "hold_out", cases=[])
        test_dataset = tasks_to_dataset(test_tasks)
        return await test_dataset.evaluate(
            evaluated_fn,
            max_concurrency=1,
            case_context_manager=task_lifecycle(domain, scope="test"),
            progress=False,
            name=f"{experiment_name or 'ho'}_test",
        )
