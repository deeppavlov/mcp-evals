"""Unified domain runner: single runner that iterates over grouper splittings."""

from functools import partial
from pathlib import Path
from typing import Any

from pydantic_ai.agent import Agent
from pydantic_ai.usage import UsageLimits
from pydantic_evals.reporting import EvaluationReport

from mcp_evals._internal.conversion import tasks_to_dataset
from mcp_evals._internal.evaluated_fn import run_agent_on_task, run_agent_on_task_with_self_correction
from mcp_evals.domain import Domain
from mcp_evals.types import DepsMaker, EvaluatedFn, RunResultProcessor, TrainingTestingCallback

from ._groupers import Grouper
from ._run_state import RunState, run_state_path
from ._utils import default_deps_maker, make_task_lifecycle


class DomainRunner:
    """Single runner: uses a grouper to get splittings, runs train then test per splitting, merges test reports."""

    def __init__(  # noqa: PLR0913
        self,
        agent: Agent[Any, Any],
        grouper: Grouper,
        deps_maker: DepsMaker | None = None,
        *,
        max_tasks: int | None = None,
        use_self_correction: bool = False,
        max_self_correction_retries: int = 3,
        start_training: TrainingTestingCallback | None = None,
        start_testing: TrainingTestingCallback | None = None,
        rerun_start_training_on_resume: bool = False,
        rerun_start_testing_on_resume: bool = False,
        run_result_processor: RunResultProcessor | None = None,
        usage_limits: UsageLimits | None = None,
        clear_state_on_success: bool = False,
        state_dir: Path | str | None = None,
    ) -> None:
        self.agent = agent
        self.deps_maker = deps_maker
        self.max_tasks = max_tasks
        self.run_result_processor = run_result_processor
        self.usage_limits = usage_limits
        self.grouper = grouper
        self.use_self_correction = use_self_correction
        self.max_self_correction_retries = max_self_correction_retries
        self.start_training = start_training
        self.start_testing = start_testing
        self.rerun_start_training_on_resume = rerun_start_training_on_resume
        self.rerun_start_testing_on_resume = rerun_start_testing_on_resume
        self.clear_state_on_success = clear_state_on_success
        self.state_dir = state_dir

    async def run(self, domain: Domain[Any], experiment_name: str) -> EvaluationReport:
        deps_maker = self.deps_maker or default_deps_maker()

        async with domain:
            if self.use_self_correction:
                evaluated_fn = partial(
                    run_agent_on_task_with_self_correction,
                    agent=self.agent,
                    toolset=domain.toolset,
                    deps_maker=deps_maker,
                    run_result_processor=self.run_result_processor,
                    usage_limits=self.usage_limits,
                    max_retries=self.max_self_correction_retries,
                )
            else:
                evaluated_fn = partial(
                    run_agent_on_task,
                    agent=self.agent,
                    toolset=domain.toolset,
                    deps_maker=deps_maker,
                    run_result_processor=self.run_result_processor,
                    usage_limits=self.usage_limits,
                )
            return await self.run_domain(domain=domain, experiment_name=experiment_name, evaluated_fn=evaluated_fn)

    async def run_domain(
        self,
        domain: Domain[Any],
        experiment_name: str,
        evaluated_fn: EvaluatedFn,
    ) -> EvaluationReport:
        tasks = list(domain.tasks())
        if self.max_tasks is not None:
            tasks = tasks[: self.max_tasks]
        n_tasks = len(tasks)
        splittings = list(self.grouper.splittings(n_tasks))
        test_reports: list[EvaluationReport] = []

        path = await run_state_path(experiment_name, state_dir=self.state_dir)
        state = await RunState.load(path, n_tasks=n_tasks, splittings=splittings)

        task_names = [t.name for t in tasks]
        for split_idx, splitting in enumerate(splittings):
            if splitting.train_indices:
                pending_train = state.pending_indices(split_idx, "train", splitting.train_indices, task_names)
                if pending_train:
                    await self._run_train_phase(
                        state,
                        split_idx,
                        pending_train,
                        tasks,
                        experiment_name,
                        evaluated_fn,
                    )

            if splitting.test_indices:
                pending_test = state.pending_indices(split_idx, "test", splitting.test_indices, task_names)
                if pending_test:
                    report = await self._run_test_phase(
                        state,
                        split_idx,
                        pending_test,
                        tasks,
                        experiment_name,
                        experiment_name,
                        evaluated_fn,
                    )
                    test_reports.append(report)

        report = _merge_test_reports(test_reports, experiment_name)
        if self.clear_state_on_success:
            await state.clear()
        return report

    async def _run_train_phase(
        self,
        state: RunState,
        split_idx: int,
        pending_train: list[int],
        tasks: list[Any],
        base_name: str,
        evaluated_fn: EvaluatedFn,
    ) -> None:
        phase_started = state.has_split_phase_started(split_idx, "train")
        run_callback = not phase_started or self.rerun_start_training_on_resume
        if run_callback and self.start_training is not None:
            await self.start_training()
        if not phase_started:
            await state.mark_split_phase_started(split_idx, "train")
        train_tasks = [tasks[i] for i in pending_train]
        train_dataset = tasks_to_dataset(train_tasks)
        await train_dataset.evaluate(
            evaluated_fn,
            max_concurrency=1,
            case_context_manager=make_task_lifecycle(state, split_idx, "train"),
            progress=False,
            name=f"{base_name}_train_{split_idx}_",
        )

    async def _run_test_phase(
        self,
        state: RunState,
        split_idx: int,
        pending_test: list[int],
        tasks: list[Any],
        base_name: str,
        experiment_name: str,
        evaluated_fn: EvaluatedFn,
    ) -> EvaluationReport:
        phase_started = state.has_split_phase_started(split_idx, "test")
        run_callback = not phase_started or self.rerun_start_testing_on_resume
        if run_callback and self.start_testing is not None:
            await self.start_testing()
        if not phase_started:
            await state.mark_split_phase_started(split_idx, "test")
            if split_idx > 0:
                await state.mark_split_finished(split_idx - 1)
        test_tasks = [tasks[i] for i in pending_test]
        test_dataset = tasks_to_dataset(test_tasks)
        return await test_dataset.evaluate(
            evaluated_fn,
            max_concurrency=1,
            case_context_manager=make_task_lifecycle(state, split_idx, "test"),
            progress=False,
            name=f"{base_name}_test_{split_idx}" if experiment_name else None,
        )


def _merge_test_reports(test_reports: list[EvaluationReport], base_name: str) -> EvaluationReport:
    if not test_reports:
        return EvaluationReport(name=base_name, cases=[])
    if len(test_reports) == 1:
        return test_reports[0]
    combined_cases = []
    for report in test_reports:
        combined_cases.extend(report.cases)
    return EvaluationReport(name=base_name, cases=combined_cases)
