"""Unified domain runner: single runner that iterates over grouper splittings."""

from functools import partial
from typing import Any

from pydantic_ai.agent import Agent
from pydantic_ai.usage import UsageLimits
from pydantic_evals.reporting import EvaluationReport

from mcp_evals._internal.conversion import tasks_to_dataset
from mcp_evals._internal.evaluated_fn import run_agent_on_task, run_agent_on_task_with_self_correction
from mcp_evals.domain import Domain
from mcp_evals.types import DepsMaker, EvaluatedFn, RunResultProcessor, TrainingTestingCallback

from ._groupers import Grouper
from ._run_state import ATTR_GLOBAL_INDEX, RunState, run_state_path
from ._utils import default_deps_maker, make_task_lifecycle, task_lifecycle


class DomainRunner:
    """Single runner: uses a grouper to get splittings, runs train then test per splitting, merges test reports."""

    def __init__(
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
        run_result_processor: RunResultProcessor | None = None,
        usage_limits: UsageLimits | None = None,
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

    async def run(self, domain: Domain[Any], experiment_name: str | None = None) -> EvaluationReport:
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
        experiment_name: str | None,
        evaluated_fn: EvaluatedFn,
    ) -> EvaluationReport:
        tasks = list(domain.tasks())
        if self.max_tasks is not None:
            tasks = tasks[: self.max_tasks]
        n_tasks = len(tasks)
        splittings = list(self.grouper.splittings(n_tasks))
        test_reports: list[EvaluationReport] = []
        base_name = experiment_name or "eval"

        state: RunState | None = None
        if experiment_name is not None:
            path = await run_state_path(experiment_name)
            state = await RunState.load(path, n_tasks=n_tasks, splittings=splittings)

        for split_idx, splitting in enumerate(splittings):
            if splitting.train_indices:
                pending_train = (
                    state.pending_indices(split_idx, "train", splitting.train_indices)
                    if state is not None
                    else list(splitting.train_indices)
                )
                if pending_train:
                    run_train_callback = state is None or not state.has_split_phase_started(split_idx, "train")
                    if run_train_callback and self.start_training is not None:
                        await self.start_training()
                    if state is not None and run_train_callback:
                        await state.mark_split_phase_started(split_idx, "train")
                    for idx in pending_train:
                        setattr(tasks[idx], ATTR_GLOBAL_INDEX, idx)
                    train_tasks = [tasks[i] for i in pending_train]
                    train_dataset = tasks_to_dataset(train_tasks)
                    case_cm = make_task_lifecycle(state, split_idx, "train") if state is not None else task_lifecycle
                    await train_dataset.evaluate(
                        evaluated_fn,
                        max_concurrency=1,
                        case_context_manager=case_cm,
                        progress=False,
                        name=f"{base_name}_train_{split_idx}_",
                    )

            if splitting.test_indices:
                pending_test = (
                    state.pending_indices(split_idx, "test", splitting.test_indices)
                    if state is not None
                    else list(splitting.test_indices)
                )
                if pending_test:
                    run_test_callback = state is None or not state.has_split_phase_started(split_idx, "test")
                    if run_test_callback and self.start_testing is not None:
                        await self.start_testing()
                    if state is not None and run_test_callback:
                        await state.mark_split_phase_started(split_idx, "test")
                        if split_idx > 0:
                            await state.mark_split_finished(split_idx - 1)
                    for idx in pending_test:
                        setattr(tasks[idx], ATTR_GLOBAL_INDEX, idx)
                    test_tasks = [tasks[i] for i in pending_test]
                    test_dataset = tasks_to_dataset(test_tasks)
                    case_cm = make_task_lifecycle(state, split_idx, "test") if state is not None else task_lifecycle
                    report = await test_dataset.evaluate(
                        evaluated_fn,
                        max_concurrency=1,
                        case_context_manager=case_cm,
                        progress=False,
                        name=f"{base_name}_test_{split_idx}" if experiment_name else None,
                    )
                    test_reports.append(report)

        # TODO(voorhs): think about proper reports aggregation
        if not test_reports:
            return EvaluationReport(name=base_name, cases=[])

        if len(test_reports) == 1:
            return test_reports[0]

        combined_cases = []
        for report in test_reports:
            combined_cases.extend(report.cases)
        return EvaluationReport(name=base_name, cases=combined_cases)
