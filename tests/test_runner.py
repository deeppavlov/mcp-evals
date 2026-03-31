"""Tests for DomainRunner class."""

from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai.agent import Agent
from pydantic_ai.mcp import MCPServer
from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator
from pydantic_evals.reporting import EvaluationReport

from mcp_evals import CVGrouper, DomainRunner, HoldOutGrouper, PlainGrouper
from mcp_evals._internal.evaluated_fn import run_agent_on_task_with_self_correction
from mcp_evals._internal.runner._run_state import (
    RunStateHeader,
    SplitPhaseStartedEvent,
    run_state_path,
)
from mcp_evals.domain import Domain
from mcp_evals.secrets import DomainSecrets, TaskSecrets
from mcp_evals.task import Task


@asynccontextmanager
async def _yield_none_cm() -> AsyncGenerator[None]:
    yield None


def _no_deps_maker(_task: Task[TaskSecrets, Any]) -> Any:
    """Deps maker that yields None (for tests that don't need real deps)."""
    return _yield_none_cm()


INTERNAL_RUN = "mcp_evals._internal.runner._domain_runner.DomainRunner.run"
INTERNAL_RUN_DOMAIN = "mcp_evals._internal.runner._domain_runner.DomainRunner.run_domain"


class ConcreteTask(Task[TaskSecrets, Any]):
    """Minimal task for runner tests."""

    goal = "Test goal"
    output_type = str
    evaluators: tuple[Evaluator[Task[TaskSecrets, Any], AgentRunResult], ...] = ()

    def __init__(self, name: str = "task", tool_retries: int = 1) -> None:
        super().__init__(tool_retries=tool_retries)
        self.name = name


class ConcreteDomain(Domain[DomainSecrets]):
    """Concrete Domain implementation for testing."""

    name = "test_domain"

    def __init__(
        self, name: str = "test_domain", tasks: list[ConcreteTask] | None = None, tool_retries: int = 1
    ) -> None:
        super().__init__(tool_retries=tool_retries)
        self.name = name
        self._task_list = tasks if tasks is not None else []

    def mcp_servers(self) -> list[MCPServer]:
        """Return empty list of MCP servers."""
        return []

    def tasks(self) -> Sequence[Task[TaskSecrets, Any]]:
        """Return tasks."""
        return self._task_list


class TestDomainRunnerInitialization:
    """Tests for DomainRunner initialization."""

    def test_stores_agent_and_grouper_correctly(self) -> None:
        """Test that DomainRunner stores agent and grouper correctly."""
        mock_agent = MagicMock(spec=Agent)
        grouper = PlainGrouper()

        runner = DomainRunner(
            agent=mock_agent,
            grouper=grouper,
        )

        assert runner.agent is mock_agent
        assert runner.grouper is grouper


@pytest.mark.asyncio
class TestDomainRunnerRun:
    """Tests for DomainRunner.run() method."""

    async def test_runs_domains_sequentially_when_called_per_domain(self) -> None:
        """When user calls run(domain, ...) per domain, each call returns that domain's report."""
        mock_agent = MagicMock(spec=Agent)
        domain1 = ConcreteDomain(name="domain1")
        domain2 = ConcreteDomain(name="domain2")
        runner = DomainRunner(
            agent=mock_agent,
            grouper=PlainGrouper(),
            deps_maker=_no_deps_maker,
        )

        mock_report1 = MagicMock(spec=EvaluationReport)
        mock_report2 = MagicMock(spec=EvaluationReport)

        call_order = []

        async def mock_run(
            domain: Domain[DomainSecrets],
            *,
            experiment_name: str | None = None,  # noqa: ARG001
        ) -> EvaluationReport:
            call_order.append(domain.name)
            if domain.name == "domain1":
                return mock_report1
            return mock_report2

        with patch(INTERNAL_RUN, side_effect=mock_run):
            report1 = await runner.run(domain1, experiment_name="test-experiment")
            report2 = await runner.run(domain2, experiment_name="test-experiment")

            assert report1 is mock_report1
            assert report2 is mock_report2
            assert call_order == ["domain1", "domain2"]

    async def test_returns_evaluation_report(self) -> None:
        """Test that run(domain, ...) returns a single EvaluationReport."""
        mock_agent = MagicMock(spec=Agent)
        domain = ConcreteDomain()
        runner = DomainRunner(
            agent=mock_agent,
            grouper=PlainGrouper(),
            deps_maker=_no_deps_maker,
        )

        mock_report = MagicMock(spec=EvaluationReport)

        with patch(INTERNAL_RUN, return_value=mock_report):
            report = await runner.run(domain, experiment_name="test-experiment")

            assert report is mock_report

    async def test_each_domain_gets_own_report_when_called_separately(self) -> None:
        """When user calls run() for each domain, each gets its own report."""
        mock_agent = MagicMock(spec=Agent)
        domain1 = ConcreteDomain(name="domain1")
        domain2 = ConcreteDomain(name="domain2")
        domain3 = ConcreteDomain(name="domain3")
        runner = DomainRunner(
            agent=mock_agent,
            grouper=PlainGrouper(),
            deps_maker=_no_deps_maker,
        )

        mock_reports = [
            MagicMock(spec=EvaluationReport),
            MagicMock(spec=EvaluationReport),
            MagicMock(spec=EvaluationReport),
        ]

        with patch(INTERNAL_RUN, side_effect=mock_reports):
            reports = [
                await runner.run(domain1, experiment_name="test-experiment"),
                await runner.run(domain2, experiment_name="test-experiment"),
                await runner.run(domain3, experiment_name="test-experiment"),
            ]

            assert len(reports) == 3
            assert all(isinstance(r, EvaluationReport) for r in reports)
            assert reports[0] is mock_reports[0]
            assert reports[1] is mock_reports[1]
            assert reports[2] is mock_reports[2]

    async def test_handles_exceptions_in_domain_execution(self) -> None:
        """Test that run(domain, ...) propagates exceptions from domain execution."""
        mock_agent = MagicMock(spec=Agent)
        domain1 = ConcreteDomain(name="domain1")
        domain2 = ConcreteDomain(name="domain2")
        runner = DomainRunner(
            agent=mock_agent,
            grouper=PlainGrouper(),
            deps_maker=_no_deps_maker,
        )

        mock_report1 = MagicMock(spec=EvaluationReport)

        async def mock_run(
            domain: Domain[DomainSecrets],
            *,
            experiment_name: str | None = None,  # noqa: ARG001
        ) -> EvaluationReport:
            if domain.name == "domain1":
                return mock_report1
            raise ValueError("Domain execution failed")

        with patch(INTERNAL_RUN, side_effect=mock_run):
            await runner.run(domain1, experiment_name="test-experiment")
            with pytest.raises(ValueError, match="Domain execution failed"):
                await runner.run(domain2, experiment_name="test-experiment")

    async def test_invokes_internal_run_once_per_run_call(self) -> None:
        """Test that each run(domain, ...) invokes the internal runner with the correct domain."""
        mock_agent = MagicMock(spec=Agent)
        domain1 = ConcreteDomain(name="domain1")
        domain2 = ConcreteDomain(name="domain2")
        runner = DomainRunner(
            agent=mock_agent,
            grouper=PlainGrouper(),
            deps_maker=_no_deps_maker,
        )

        with patch(INTERNAL_RUN, new_callable=AsyncMock) as mock_internal_run:
            mock_internal_run.return_value = MagicMock(spec=EvaluationReport)
            await runner.run(domain1, experiment_name="test-experiment")
            await runner.run(domain2, experiment_name="test-experiment")

            assert mock_internal_run.call_count == 2
            assert mock_internal_run.call_args_list[0].args[0] is domain1
            assert mock_internal_run.call_args_list[1].args[0] is domain2

    async def test_run_passes_experiment_name_to_internal_runner(self) -> None:
        """Test that run(domain, experiment_name=...) forwards experiment_name."""
        mock_agent = MagicMock(spec=Agent)
        domain = ConcreteDomain()
        runner = DomainRunner(
            agent=mock_agent,
            grouper=PlainGrouper(),
        )

        with patch(INTERNAL_RUN, new_callable=AsyncMock) as mock_internal_run:
            mock_internal_run.return_value = MagicMock(spec=EvaluationReport)
            await runner.run(domain, experiment_name="exp")

            mock_internal_run.assert_called_once()
            assert mock_internal_run.call_args.kwargs["experiment_name"] == "exp"

    async def test_run_with_deps_maker_uses_that_deps_maker(self) -> None:
        """Test that DomainRunner(deps_maker=...) stores and uses that deps_maker."""
        mock_agent = MagicMock(spec=Agent)
        domain = ConcreteDomain()
        custom_factory = _no_deps_maker
        runner = DomainRunner(
            agent=mock_agent,
            grouper=PlainGrouper(),
            deps_maker=custom_factory,
        )

        with patch(INTERNAL_RUN, new_callable=AsyncMock) as mock_internal_run:
            mock_internal_run.return_value = MagicMock(spec=EvaluationReport)
            await runner.run(domain, experiment_name="test-experiment")

            mock_internal_run.assert_called_once()
            assert runner.deps_maker is custom_factory


# Internal run_domain path for HO, CV, self-correction (patch to mock without running agent)
INTERNAL_RUN_HOLD_OUT = INTERNAL_RUN_DOMAIN
INTERNAL_RUN_CV = INTERNAL_RUN_DOMAIN
INTERNAL_RUN_SELF_CORRECTION = INTERNAL_RUN_DOMAIN


@pytest.mark.asyncio
class TestDomainRunnerHoldOut:
    """Tests for DomainRunner with HoldOutGrouper."""

    async def test_hold_out_returns_one_report_per_run(self) -> None:
        """Hold-out runner returns one EvaluationReport per run(domain, ...)."""
        mock_agent = MagicMock(spec=Agent)
        domain = ConcreteDomain(tasks=[ConcreteTask(name=f"t{i}") for i in range(5)])
        runner = DomainRunner(
            agent=mock_agent,
            grouper=HoldOutGrouper(test_ratio=0.2),
            deps_maker=_no_deps_maker,
        )
        mock_report = MagicMock(spec=EvaluationReport)
        mock_report.cases = [MagicMock(), MagicMock()]  # ~20% of 5 -> 1 or 2 test cases

        with patch(INTERNAL_RUN_DOMAIN, new_callable=AsyncMock, return_value=mock_report):
            report = await runner.run(domain, experiment_name="test-experiment")

        assert report is mock_report

    async def test_hold_out_callbacks_invoked_in_order(self, tmp_path: Path) -> None:
        """start_training is awaited before training run, start_testing before test run."""
        mock_agent = MagicMock(spec=Agent)
        tasks = [ConcreteTask(name=f"t{i}") for i in range(10)]
        domain = ConcreteDomain(tasks=tasks)
        start_training = AsyncMock()
        start_testing = AsyncMock()
        runner = DomainRunner(
            agent=mock_agent,
            grouper=HoldOutGrouper(test_ratio=0.2),
            deps_maker=_no_deps_maker,
            start_training=start_training,
            start_testing=start_testing,
            state_dir=tmp_path,
        )

        with patch(
            "mcp_evals._internal.runner._domain_runner.tasks_to_dataset",
            side_effect=lambda ts: MagicMock(
                evaluate=AsyncMock(
                    return_value=MagicMock(
                        spec=EvaluationReport,
                        cases=[MagicMock() for _ in range(len(ts))],
                    )
                )
            ),
        ):
            await runner.run(domain, experiment_name="test-experiment")

        assert start_training.await_count == 1
        assert start_testing.await_count == 1

    async def test_hold_out_callbacks_receive_phase_name(self, tmp_path: Path) -> None:
        """Callbacks that accept phase_name receive 'train_{split_idx}' and 'test_{split_idx}'."""
        seen_phase_names: list[tuple[str, str]] = []

        async def on_training(phase_name: str, _run_ctx: Any) -> None:
            seen_phase_names.append(("train", phase_name or ""))

        async def on_testing(phase_name: str, _run_ctx: Any) -> None:
            seen_phase_names.append(("test", phase_name or ""))

        mock_agent = MagicMock(spec=Agent)
        tasks = [ConcreteTask(name=f"t{i}") for i in range(10)]
        domain = ConcreteDomain(tasks=tasks)
        runner = DomainRunner(
            agent=mock_agent,
            grouper=HoldOutGrouper(test_ratio=0.2),
            deps_maker=_no_deps_maker,
            start_training=on_training,
            start_testing=on_testing,
            state_dir=tmp_path,
        )
        with patch(
            "mcp_evals._internal.runner._domain_runner.tasks_to_dataset",
            side_effect=lambda ts: MagicMock(
                evaluate=AsyncMock(
                    return_value=MagicMock(
                        spec=EvaluationReport,
                        cases=[MagicMock() for _ in range(len(ts))],
                    )
                )
            ),
        ):
            await runner.run(domain, experiment_name="test-experiment")

        assert seen_phase_names == [("train", "train_0"), ("test", "test_0")]

    async def test_hold_out_callbacks_receive_run_ctx(self, tmp_path: Path) -> None:
        """Callbacks that accept run_ctx receive phase-to-tasks mapping."""
        seen: list[tuple[str, list[str]]] = []

        async def on_training(phase_name: str, run_ctx: Any) -> None:
            task_names = [task.name for task in run_ctx["phase_to_tasks"][phase_name]]
            seen.append((phase_name, task_names))

        async def on_testing(phase_name: str, run_ctx: Any) -> None:
            task_names = [task.name for task in run_ctx["phase_to_tasks"][phase_name]]
            seen.append((phase_name, task_names))

        mock_agent = MagicMock(spec=Agent)
        tasks = [ConcreteTask(name=f"t{i}") for i in range(10)]
        domain = ConcreteDomain(tasks=tasks)
        runner = DomainRunner(
            agent=mock_agent,
            grouper=HoldOutGrouper(test_ratio=0.2),
            deps_maker=_no_deps_maker,
            start_training=on_training,
            start_testing=on_testing,
            state_dir=tmp_path,
        )
        with patch(
            "mcp_evals._internal.runner._domain_runner.tasks_to_dataset",
            side_effect=lambda ts: MagicMock(
                evaluate=AsyncMock(
                    return_value=MagicMock(
                        spec=EvaluationReport,
                        cases=[MagicMock() for _ in range(len(ts))],
                    )
                )
            ),
        ):
            await runner.run(domain, experiment_name="test-experiment")

        assert seen[0][0] == "train_0"
        assert seen[1][0] == "test_0"
        assert set(seen[0][1] + seen[1][1]) == {f"t{i}" for i in range(10)}

    async def test_skip_training_tasks_runs_training_callback_but_skips_train_evaluation(self, tmp_path: Path) -> None:
        """With skip_training_tasks=True, training callback runs but train dataset is not evaluated."""
        mock_agent = MagicMock(spec=Agent)
        tasks = [ConcreteTask(name=f"t{i}") for i in range(10)]
        domain = ConcreteDomain(tasks=tasks)
        start_training = AsyncMock()
        start_testing = AsyncMock()
        runner = DomainRunner(
            agent=mock_agent,
            grouper=HoldOutGrouper(test_ratio=0.2),
            deps_maker=_no_deps_maker,
            start_training=start_training,
            start_testing=start_testing,
            skip_training_tasks=True,
            state_dir=tmp_path,
        )

        datasets: list[Any] = []

        def _make_dataset(ts: list[Any]) -> Any:
            dataset = MagicMock(
                evaluate=AsyncMock(
                    return_value=MagicMock(
                        spec=EvaluationReport,
                        cases=[MagicMock() for _ in range(len(ts))],
                    )
                )
            )
            datasets.append(dataset)
            return dataset

        with patch(
            "mcp_evals._internal.runner._domain_runner.tasks_to_dataset",
            side_effect=_make_dataset,
        ):
            await runner.run(domain, experiment_name="test-experiment")

        assert start_training.await_count == 1
        assert start_testing.await_count == 1
        assert len(datasets) == 1


@pytest.mark.asyncio
class TestDomainRunnerCrossValidation:
    """Tests for DomainRunner with CVGrouper."""

    async def test_cv_returns_one_report_per_run(self) -> None:
        """CV runner returns one merged EvaluationReport per run(domain, ...)."""
        mock_agent = MagicMock(spec=Agent)
        domain = ConcreteDomain(tasks=[ConcreteTask(name=f"t{i}") for i in range(10)])
        runner = DomainRunner(
            agent=mock_agent,
            grouper=CVGrouper(n_splits=5),
            deps_maker=_no_deps_maker,
        )
        mock_report = MagicMock(spec=EvaluationReport)
        mock_report.cases = [MagicMock() for _ in range(10)]

        with patch(INTERNAL_RUN_DOMAIN, new_callable=AsyncMock, return_value=mock_report):
            report = await runner.run(domain, experiment_name="test-experiment")

        assert report is mock_report

    async def test_cv_callbacks_invoked_per_fold(self, tmp_path: Path) -> None:
        """start_training and start_testing are awaited K times (once per fold)."""
        mock_agent = MagicMock(spec=Agent)
        tasks = [ConcreteTask(name=f"t{i}") for i in range(6)]
        domain = ConcreteDomain(tasks=tasks)
        start_training = AsyncMock()
        start_testing = AsyncMock()
        runner = DomainRunner(
            agent=mock_agent,
            grouper=CVGrouper(n_splits=3),
            deps_maker=_no_deps_maker,
            start_training=start_training,
            start_testing=start_testing,
            state_dir=tmp_path,
        )

        with patch(
            "mcp_evals._internal.runner._domain_runner.tasks_to_dataset",
            side_effect=lambda ts: MagicMock(
                evaluate=AsyncMock(
                    return_value=MagicMock(
                        spec=EvaluationReport,
                        cases=[MagicMock() for _ in range(len(ts))],
                    )
                )
            ),
        ):
            await runner.run(domain, experiment_name="test-experiment")

        assert start_training.await_count == 3
        assert start_testing.await_count == 3


@pytest.mark.asyncio
class TestDomainRunnerResumeCallbacks:
    """Tests for rerun_start_*_on_resume when resuming from checkpoint."""

    async def _write_state_with_phase_started(
        self,
        tmp_path: Path,
        experiment_name: str,
        n_tasks: int,
        split_idx: int,
        phase: Literal["train", "test"],
    ) -> None:
        """Write state file with given phase already marked started (simulate resume)."""
        splittings = list(HoldOutGrouper(test_ratio=0.2).splittings(n_tasks))
        fp = [[len(s.train_indices), len(s.test_indices)] for s in splittings]
        path = await run_state_path(experiment_name, state_dir=tmp_path)
        await path.parent.mkdir(parents=True, exist_ok=True)
        header = RunStateHeader(n_tasks=n_tasks, splitting_fingerprint=fp)
        lines = [
            header.model_dump_json(),
            SplitPhaseStartedEvent(split_idx=split_idx, phase=phase).model_dump_json(),
        ]
        async with await path.open("w") as f:
            await f.write("\n".join(lines) + "\n")

    async def test_resume_skips_start_training_by_default(self, tmp_path: Path) -> None:
        """When resuming with train phase already started, start_training is not called by default."""
        await self._write_state_with_phase_started(tmp_path, "exp", 10, 0, "train")
        mock_agent = MagicMock(spec=Agent)
        tasks = [ConcreteTask(name=f"t{i}") for i in range(10)]
        domain = ConcreteDomain(tasks=tasks)
        start_training = AsyncMock()
        start_testing = AsyncMock()
        runner = DomainRunner(
            agent=mock_agent,
            grouper=HoldOutGrouper(test_ratio=0.2),
            deps_maker=_no_deps_maker,
            start_training=start_training,
            start_testing=start_testing,
            state_dir=tmp_path,
        )
        with patch(
            "mcp_evals._internal.runner._domain_runner.tasks_to_dataset",
            side_effect=lambda ts: MagicMock(
                evaluate=AsyncMock(
                    return_value=MagicMock(
                        spec=EvaluationReport,
                        cases=[MagicMock() for _ in range(len(ts))],
                    )
                )
            ),
        ):
            await runner.run(domain, experiment_name="exp")

        assert start_training.await_count == 0
        assert start_testing.await_count == 1

    async def test_resume_reruns_start_training_when_opted_in(self, tmp_path: Path) -> None:
        """When rerun_start_training_on_resume=True, start_training is called again on resume."""
        await self._write_state_with_phase_started(tmp_path, "exp", 10, 0, "train")
        mock_agent = MagicMock(spec=Agent)
        tasks = [ConcreteTask(name=f"t{i}") for i in range(10)]
        domain = ConcreteDomain(tasks=tasks)
        start_training = AsyncMock()
        start_testing = AsyncMock()
        runner = DomainRunner(
            agent=mock_agent,
            grouper=HoldOutGrouper(test_ratio=0.2),
            deps_maker=_no_deps_maker,
            start_training=start_training,
            start_testing=start_testing,
            rerun_start_training_on_resume=True,
            state_dir=tmp_path,
        )
        with patch(
            "mcp_evals._internal.runner._domain_runner.tasks_to_dataset",
            side_effect=lambda ts: MagicMock(
                evaluate=AsyncMock(
                    return_value=MagicMock(
                        spec=EvaluationReport,
                        cases=[MagicMock() for _ in range(len(ts))],
                    )
                )
            ),
        ):
            await runner.run(domain, experiment_name="exp")

        assert start_training.await_count == 1
        assert start_testing.await_count == 1

    async def test_resume_skips_start_testing_by_default(self, tmp_path: Path) -> None:
        """When resuming with test phase already started, start_testing is not called by default."""
        await self._write_state_with_phase_started(tmp_path, "exp", 10, 0, "test")
        mock_agent = MagicMock(spec=Agent)
        tasks = [ConcreteTask(name=f"t{i}") for i in range(10)]
        domain = ConcreteDomain(tasks=tasks)
        start_training = AsyncMock()
        start_testing = AsyncMock()
        runner = DomainRunner(
            agent=mock_agent,
            grouper=HoldOutGrouper(test_ratio=0.2),
            deps_maker=_no_deps_maker,
            start_training=start_training,
            start_testing=start_testing,
            state_dir=tmp_path,
        )
        with patch(
            "mcp_evals._internal.runner._domain_runner.tasks_to_dataset",
            side_effect=lambda ts: MagicMock(
                evaluate=AsyncMock(
                    return_value=MagicMock(
                        spec=EvaluationReport,
                        cases=[MagicMock() for _ in range(len(ts))],
                    )
                )
            ),
        ):
            await runner.run(domain, experiment_name="exp")

        assert start_training.await_count == 1
        assert start_testing.await_count == 0

    async def test_resume_reruns_start_testing_when_opted_in(self, tmp_path: Path) -> None:
        """When rerun_start_testing_on_resume=True, start_testing is called again on resume."""
        await self._write_state_with_phase_started(tmp_path, "exp", 10, 0, "test")
        mock_agent = MagicMock(spec=Agent)
        tasks = [ConcreteTask(name=f"t{i}") for i in range(10)]
        domain = ConcreteDomain(tasks=tasks)
        start_training = AsyncMock()
        start_testing = AsyncMock()
        runner = DomainRunner(
            agent=mock_agent,
            grouper=HoldOutGrouper(test_ratio=0.2),
            deps_maker=_no_deps_maker,
            start_training=start_training,
            start_testing=start_testing,
            rerun_start_testing_on_resume=True,
            state_dir=tmp_path,
        )
        with patch(
            "mcp_evals._internal.runner._domain_runner.tasks_to_dataset",
            side_effect=lambda ts: MagicMock(
                evaluate=AsyncMock(
                    return_value=MagicMock(
                        spec=EvaluationReport,
                        cases=[MagicMock() for _ in range(len(ts))],
                    )
                )
            ),
        ):
            await runner.run(domain, experiment_name="exp")

        assert start_training.await_count == 1
        assert start_testing.await_count == 1


@pytest.mark.asyncio
class TestDomainRunnerSelfCorrection:
    """Tests for DomainRunner with use_self_correction=True."""

    async def test_self_correction_returns_one_report_per_run(self) -> None:
        """Self-correction runner returns one EvaluationReport per run(domain, ...)."""
        mock_agent = MagicMock(spec=Agent)
        domain = ConcreteDomain(tasks=[ConcreteTask(name=f"t{i}") for i in range(3)])
        runner = DomainRunner(
            agent=mock_agent,
            grouper=PlainGrouper(),
            deps_maker=_no_deps_maker,
            use_self_correction=True,
            max_self_correction_retries=2,
        )
        mock_report = MagicMock(spec=EvaluationReport)
        mock_report.cases = [MagicMock(), MagicMock(), MagicMock()]

        with patch(
            INTERNAL_RUN_DOMAIN,
            new_callable=AsyncMock,
            return_value=mock_report,
        ):
            report = await runner.run(domain, experiment_name="test-experiment")

        assert report is mock_report

    async def test_self_correction_uses_correct_internal_runner(self) -> None:
        """use_self_correction=True creates DomainRunner with correct params."""
        mock_agent = MagicMock(spec=Agent)
        domain = ConcreteDomain()
        runner = DomainRunner(
            agent=mock_agent,
            grouper=PlainGrouper(),
            deps_maker=_no_deps_maker,
            use_self_correction=True,
            max_self_correction_retries=5,
        )
        mock_report = MagicMock(spec=EvaluationReport)

        with patch(
            INTERNAL_RUN_DOMAIN,
            new_callable=AsyncMock,
            return_value=mock_report,
        ) as mock_run:
            await runner.run(domain, experiment_name="test-experiment")
            mock_run.assert_called_once()
            assert mock_run.call_args.kwargs["domain"] is domain

    async def test_self_correction_max_tasks_limits_cases(self, tmp_path: Path) -> None:
        """With max_tasks=2, self-correction report contains at most 2 cases."""
        mock_agent = MagicMock(spec=Agent)
        domain = ConcreteDomain(tasks=[ConcreteTask(name=f"t{i}") for i in range(5)])
        runner = DomainRunner(
            agent=mock_agent,
            grouper=PlainGrouper(),
            deps_maker=_no_deps_maker,
            use_self_correction=True,
            max_tasks=2,
            state_dir=tmp_path,
        )
        mock_result = MagicMock(spec=AgentRunResult)

        with patch(
            "mcp_evals._internal.evaluated_fn.run_agent_on_task_with_self_correction",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            report = await runner.run(domain, experiment_name="test-experiment")

        assert len(report.cases) == 2


@pytest.mark.asyncio
class TestRunAgentOnTaskWithSelfCorrection:
    """Tests for run_agent_on_task_with_self_correction evaluated fn."""

    async def test_retries_on_evaluator_failure_and_passes_feedback(self) -> None:
        """When evaluator fails, agent is re-run with augmented goal containing feedback."""

        mock_agent = MagicMock(spec=Agent)
        mock_result = MagicMock(spec=AgentRunResult)
        mock_result.output = MagicMock()
        mock_result.all_messages = MagicMock(return_value=[])
        mock_agent.run = AsyncMock(return_value=mock_result)

        failing_evaluator = AsyncMock(
            side_effect=[
                EvaluationReason(value=0.0, reason="Date order violation"),
                1.0,
            ]
        )

        class ChronologicalOrderEvaluator(Evaluator):
            """Evaluator with a proper name (no 'name' attr, uses __class__.__name__)."""

            evaluate = failing_evaluator

        task = ConcreteTask(name="retry_task")
        task.evaluators = (ChronologicalOrderEvaluator(),)

        mock_toolset = MagicMock()

        async with task:
            result = await run_agent_on_task_with_self_correction(
                task,
                agent=mock_agent,
                toolset=mock_toolset,
                deps_maker=_no_deps_maker,
                max_retries=3,
            )

        assert result is mock_result
        assert mock_agent.run.await_count == 2
        # First call: original goal
        assert mock_agent.run.call_args_list[0].args[0] == "Test goal"
        # Second call: feedback only (Evaluation results format)
        second_inputs = mock_agent.run.call_args_list[1].args[0]
        assert "Evaluation results" in second_inputs
        assert "Date order violation" in second_inputs
        assert "Please, try to fix these errors" in second_inputs
        assert "ChronologicalOrderEvaluator" in second_inputs

    async def test_returns_immediately_when_all_evaluators_pass(self) -> None:
        """When all evaluators pass on first try, no retries occur."""

        mock_agent = MagicMock(spec=Agent)
        mock_result = MagicMock(spec=AgentRunResult)
        mock_result.all_messages = MagicMock(return_value=[])
        mock_agent.run = AsyncMock(return_value=mock_result)

        passing_evaluator = AsyncMock(return_value=1.0)

        task = ConcreteTask(name="pass_task")
        task.evaluators = (MagicMock(evaluate=passing_evaluator),)

        mock_toolset = MagicMock()

        async with task:
            result = await run_agent_on_task_with_self_correction(
                task,
                agent=mock_agent,
                toolset=mock_toolset,
                deps_maker=_no_deps_maker,
                max_retries=3,
            )

        assert result is mock_result
        assert mock_agent.run.await_count == 1

    async def test_stops_after_max_retries(self) -> None:
        """When evaluators never pass, stops after max_retries and returns last result."""

        mock_agent = MagicMock(spec=Agent)
        mock_result = MagicMock(spec=AgentRunResult)
        mock_result.all_messages = MagicMock(return_value=[])
        mock_agent.run = AsyncMock(return_value=mock_result)

        always_failing = AsyncMock(return_value=EvaluationReason(value=0.0, reason="Always fails"))

        task = ConcreteTask(name="fail_task")
        task.evaluators = (MagicMock(evaluate=always_failing),)

        mock_toolset = MagicMock()

        async with task:
            result = await run_agent_on_task_with_self_correction(
                task,
                agent=mock_agent,
                toolset=mock_toolset,
                deps_maker=_no_deps_maker,
                max_retries=3,
            )

        assert result is mock_result
        assert mock_agent.run.await_count == 3


@pytest.mark.asyncio
class TestDomainRunnerMaxTasks:
    """Tests for max_tasks limiting the number of tasks run per domain."""

    async def test_inference_only_max_tasks_limits_cases(self, tmp_path: Path) -> None:
        """With max_tasks=2, report contains at most 2 cases (first 2 tasks)."""
        mock_agent = MagicMock(spec=Agent)
        domain = ConcreteDomain(tasks=[ConcreteTask(name=f"t{i}") for i in range(5)])
        runner = DomainRunner(
            agent=mock_agent,
            grouper=PlainGrouper(),
            deps_maker=_no_deps_maker,
            max_tasks=2,
            state_dir=tmp_path,
        )
        mock_result = MagicMock(spec=AgentRunResult)

        with patch(
            "mcp_evals._internal.runner._domain_runner.run_agent_on_task",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            report = await runner.run(domain, experiment_name="test-experiment")

        assert len(report.cases) == 2

    async def test_hold_out_max_tasks_limits_task_list(self, tmp_path: Path) -> None:
        """With max_tasks=2, hold_out_split is called with n_tasks=2."""
        mock_agent = MagicMock(spec=Agent)
        domain = ConcreteDomain(tasks=[ConcreteTask(name=f"t{i}") for i in range(5)])
        runner = DomainRunner(
            agent=mock_agent,
            grouper=HoldOutGrouper(test_ratio=0.5),
            deps_maker=_no_deps_maker,
            max_tasks=2,
            state_dir=tmp_path,
        )
        call_args: list[tuple[int, float, int | None]] = []

        def capture_hold_out(n_tasks: int, test_ratio: float, random_state: int | None) -> Any:
            call_args.append((n_tasks, test_ratio, random_state))
            from mcp_evals._internal.runner._splits import hold_out_split as real  # noqa: PLC0415

            return real(n_tasks, test_ratio, random_state)

        with (
            patch(
                "mcp_evals._internal.runner._groupers.hold_out_split",
                side_effect=capture_hold_out,
            ),
            patch(
                "mcp_evals._internal.runner._domain_runner.tasks_to_dataset",
                side_effect=lambda ts: MagicMock(
                    evaluate=AsyncMock(
                        return_value=MagicMock(
                            spec=EvaluationReport,
                            cases=[MagicMock() for _ in range(len(ts))],
                        )
                    )
                ),
            ),
        ):
            await runner.run(domain, experiment_name="test-experiment")

        assert len(call_args) == 1
        assert call_args[0][0] == 2

    async def test_cv_max_tasks_limits_task_list(self, tmp_path: Path) -> None:
        """With max_tasks=2, k_fold_split is called with n_tasks=2."""
        mock_agent = MagicMock(spec=Agent)
        domain = ConcreteDomain(tasks=[ConcreteTask(name=f"t{i}") for i in range(5)])
        runner = DomainRunner(
            agent=mock_agent,
            grouper=CVGrouper(n_splits=2),
            deps_maker=_no_deps_maker,
            max_tasks=2,
            state_dir=tmp_path,
        )
        call_args: list[int] = []

        def capture_k_fold(n_tasks: int, n_splits: int, random_state: int | None) -> Any:
            call_args.append(n_tasks)
            from mcp_evals._internal.runner._splits import k_fold_split as real  # noqa: PLC0415

            return real(n_tasks, n_splits, random_state)

        with (
            patch(
                "mcp_evals._internal.runner._groupers.k_fold_split",
                side_effect=capture_k_fold,
            ),
            patch(
                "mcp_evals._internal.runner._domain_runner.tasks_to_dataset",
                side_effect=lambda ts: MagicMock(
                    evaluate=AsyncMock(
                        return_value=MagicMock(
                            spec=EvaluationReport,
                            cases=[MagicMock() for _ in range(len(ts))],
                        )
                    )
                ),
            ),
        ):
            await runner.run(domain, experiment_name="test-experiment")

        assert len(call_args) == 1
        assert call_args[0] == 2
