"""Tests for BenchmarkRunner class."""

from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai.agent import Agent
from pydantic_ai.mcp import MCPServer
from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator
from pydantic_evals.reporting import EvaluationReport

from mcp_evals._internal.evaluated_fn import run_agent_on_task_with_self_correction
from mcp_evals.domain import Domain
from mcp_evals.runner import BenchmarkRunner
from mcp_evals.secrets import DomainSecrets, TaskSecrets
from mcp_evals.task import Task
from mcp_evals.types import Runner


@asynccontextmanager
async def _yield_none_cm() -> AsyncGenerator[None]:
    yield None


def _no_deps_maker(_task: Task[TaskSecrets, Any]) -> Any:
    """Deps maker that yields None (for tests that don't need real deps)."""
    return _yield_none_cm()


INTERNAL_RUN = "mcp_evals._internal.runner._domain_runner.DomainRunnerInferenceOnly.run"


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


class TestBenchmarkRunnerInitialization:
    """Tests for BenchmarkRunner initialization."""

    def test_stores_agent_and_domains_correctly(self) -> None:
        """Test that BenchmarkRunner stores agent and domains correctly."""
        mock_agent = MagicMock(spec=Agent)
        domain1 = ConcreteDomain(name="domain1")
        domain2 = ConcreteDomain(name="domain2")

        runner = BenchmarkRunner(
            agent=mock_agent,
            domains=[domain1, domain2],
            runner=Runner.INFERENCE_ONLY,
        )

        assert runner.agent is mock_agent
        assert len(runner.domains) == 2
        assert domain1 in runner.domains
        assert domain2 in runner.domains


@pytest.mark.asyncio
class TestBenchmarkRunnerRun:
    """Tests for BenchmarkRunner.run() method."""

    async def test_runs_all_domains_sequentially(self) -> None:
        """Test that run() runs all domains sequentially."""
        mock_agent = MagicMock(spec=Agent)
        domain1 = ConcreteDomain(name="domain1")
        domain2 = ConcreteDomain(name="domain2")
        runner = BenchmarkRunner(
            agent=mock_agent,
            domains=[domain1, domain2],
            runner=Runner.INFERENCE_ONLY,
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
            reports = await runner.run()

            assert len(reports) == 2
            assert reports[0] is mock_report1
            assert reports[1] is mock_report2
            assert call_order == ["domain1", "domain2"]

    async def test_returns_list_of_evaluation_reports(self) -> None:
        """Test that run() returns list of EvaluationReport."""
        mock_agent = MagicMock(spec=Agent)
        domain = ConcreteDomain()
        runner = BenchmarkRunner(
            agent=mock_agent,
            domains=[domain],
            runner=Runner.INFERENCE_ONLY,
            deps_maker=_no_deps_maker,
        )

        mock_report = MagicMock(spec=EvaluationReport)

        with patch(INTERNAL_RUN, return_value=mock_report):
            reports = await runner.run()

            assert isinstance(reports, list)
            assert len(reports) == 1
            assert reports[0] is mock_report

    async def test_each_domain_gets_own_report(self) -> None:
        """Test that each domain gets its own report."""
        mock_agent = MagicMock(spec=Agent)
        domain1 = ConcreteDomain(name="domain1")
        domain2 = ConcreteDomain(name="domain2")
        domain3 = ConcreteDomain(name="domain3")
        runner = BenchmarkRunner(
            agent=mock_agent,
            domains=[domain1, domain2, domain3],
            runner=Runner.INFERENCE_ONLY,
            deps_maker=_no_deps_maker,
        )

        mock_reports = [
            MagicMock(spec=EvaluationReport),
            MagicMock(spec=EvaluationReport),
            MagicMock(spec=EvaluationReport),
        ]

        with patch(INTERNAL_RUN, side_effect=mock_reports):
            reports = await runner.run()

            assert len(reports) == 3
            assert all(isinstance(r, EvaluationReport) for r in reports)
            assert reports[0] is mock_reports[0]
            assert reports[1] is mock_reports[1]
            assert reports[2] is mock_reports[2]

    async def test_handles_empty_domains_list(self) -> None:
        """Test that run() handles empty domains list."""
        mock_agent = MagicMock(spec=Agent)
        runner = BenchmarkRunner(
            agent=mock_agent,
            domains=[],
            runner=Runner.INFERENCE_ONLY,
        )

        reports = await runner.run()

        assert isinstance(reports, list)
        assert len(reports) == 0

    async def test_handles_exceptions_in_domain_execution(self) -> None:
        """Test that run() handles exceptions in domain execution."""
        mock_agent = MagicMock(spec=Agent)
        domain1 = ConcreteDomain(name="domain1")
        domain2 = ConcreteDomain(name="domain2")
        runner = BenchmarkRunner(
            agent=mock_agent,
            domains=[domain1, domain2],
            runner=Runner.INFERENCE_ONLY,
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

        with (
            patch(INTERNAL_RUN, side_effect=mock_run),
            pytest.raises(ValueError, match="Domain execution failed"),
        ):
            await runner.run()

    async def test_invokes_runner_once_per_domain(self) -> None:
        """Test that run() invokes the domain runner once per domain with correct domains."""
        mock_agent = MagicMock(spec=Agent)
        domain1 = ConcreteDomain(name="domain1")
        domain2 = ConcreteDomain(name="domain2")
        runner = BenchmarkRunner(
            agent=mock_agent,
            domains=[domain1, domain2],
            runner=Runner.INFERENCE_ONLY,
            deps_maker=_no_deps_maker,
        )

        with patch(INTERNAL_RUN, new_callable=AsyncMock) as mock_internal_run:
            mock_internal_run.return_value = MagicMock(spec=EvaluationReport)
            await runner.run()

            assert mock_internal_run.call_count == 2
            # Patched method is called as run(domain, experiment_name=...); domain is first positional
            assert mock_internal_run.call_args_list[0].args[0] is domain1
            assert mock_internal_run.call_args_list[1].args[0] is domain2

    async def test_run_passes_experiment_name_to_internal_runner(self) -> None:
        """Test that run() forwards experiment_name from constructor to internal runner."""
        mock_agent = MagicMock(spec=Agent)
        domain = ConcreteDomain()
        runner = BenchmarkRunner(
            agent=mock_agent,
            domains=[domain],
            runner=Runner.INFERENCE_ONLY,
            experiment_name="exp",
        )

        with patch(INTERNAL_RUN, new_callable=AsyncMock) as mock_internal_run:
            mock_internal_run.return_value = MagicMock(spec=EvaluationReport)
            await runner.run()

            mock_internal_run.assert_called_once()
            assert mock_internal_run.call_args.kwargs["experiment_name"] == "exp"

    async def test_run_with_deps_maker_uses_internal_runner(self) -> None:
        """Test that BenchmarkRunner(deps_maker=...) creates runner that uses that deps_maker."""
        mock_agent = MagicMock(spec=Agent)
        domain = ConcreteDomain()
        custom_factory = _no_deps_maker
        runner = BenchmarkRunner(
            agent=mock_agent,
            domains=[domain],
            runner=Runner.INFERENCE_ONLY,
            deps_maker=custom_factory,
        )

        with patch(INTERNAL_RUN, new_callable=AsyncMock) as mock_internal_run:
            mock_internal_run.return_value = MagicMock(spec=EvaluationReport)
            await runner.run()

            mock_internal_run.assert_called_once()
            assert runner.deps_maker is custom_factory


# Internal run paths for HO, CV, and self-correction (so we can patch and assert without running agent)
INTERNAL_RUN_HOLD_OUT = "mcp_evals._internal.runner._hold_out_runner.DomainRunnerHoldOut.run_domain"
INTERNAL_RUN_CV = "mcp_evals._internal.runner._cv_runner.DomainRunnerCrossValidation.run_domain"
INTERNAL_RUN_SELF_CORRECTION = (
    "mcp_evals._internal.runner._self_correction_runner.DomainRunnerSelfCorrection.run_domain"
)


@pytest.mark.asyncio
class TestBenchmarkRunnerHoldOut:
    """Tests for BenchmarkRunner with Runner.HOLD_OUT."""

    async def test_hold_out_returns_one_report_per_domain(self) -> None:
        """Hold-out runner returns one EvaluationReport per domain."""
        mock_agent = MagicMock(spec=Agent)
        domain = ConcreteDomain(tasks=[ConcreteTask(name=f"t{i}") for i in range(5)])
        runner = BenchmarkRunner(
            agent=mock_agent,
            domains=[domain],
            runner=Runner.HOLD_OUT,
            deps_maker=_no_deps_maker,
            hold_out_test_ratio=0.2,
        )
        mock_report = MagicMock(spec=EvaluationReport)
        mock_report.cases = [MagicMock(), MagicMock()]  # ~20% of 5 -> 1 or 2 test cases

        with patch(INTERNAL_RUN_HOLD_OUT, new_callable=AsyncMock, return_value=mock_report):
            reports = await runner.run()

        assert len(reports) == 1
        assert reports[0] is mock_report

    async def test_hold_out_callbacks_invoked_in_order(self) -> None:
        """start_training is awaited before training run, start_testing before test run."""
        mock_agent = MagicMock(spec=Agent)
        tasks = [ConcreteTask(name=f"t{i}") for i in range(10)]
        domain = ConcreteDomain(tasks=tasks)
        start_training = AsyncMock()
        start_testing = AsyncMock()
        runner = BenchmarkRunner(
            agent=mock_agent,
            domains=[domain],
            runner=Runner.HOLD_OUT,
            deps_maker=_no_deps_maker,
            hold_out_test_ratio=0.2,
            start_training=start_training,
            start_testing=start_testing,
        )

        with patch(
            "mcp_evals._internal.runner._hold_out_runner.tasks_to_dataset",
            side_effect=lambda ts: MagicMock(
                evaluate=AsyncMock(
                    return_value=MagicMock(
                        spec=EvaluationReport,
                        cases=[MagicMock() for _ in range(len(ts))],
                    )
                )
            ),
        ):
            reports = await runner.run()

        assert len(reports) == 1
        assert start_training.await_count == 1
        assert start_testing.await_count == 1
        assert start_training.await_count == 1
        assert start_testing.await_count == 1


@pytest.mark.asyncio
class TestBenchmarkRunnerCrossValidation:
    """Tests for BenchmarkRunner with Runner.CROSS_VALIDATION."""

    async def test_cv_returns_one_report_per_domain(self) -> None:
        """CV runner returns one merged EvaluationReport per domain."""
        mock_agent = MagicMock(spec=Agent)
        domain = ConcreteDomain(tasks=[ConcreteTask(name=f"t{i}") for i in range(10)])
        runner = BenchmarkRunner(
            agent=mock_agent,
            domains=[domain],
            runner=Runner.CROSS_VALIDATION,
            deps_maker=_no_deps_maker,
            cv_n_splits=5,
        )
        mock_report = MagicMock(spec=EvaluationReport)
        mock_report.cases = [MagicMock() for _ in range(10)]

        with patch(INTERNAL_RUN_CV, new_callable=AsyncMock, return_value=mock_report):
            reports = await runner.run()

        assert len(reports) == 1
        assert reports[0] is mock_report

    async def test_cv_callbacks_invoked_per_fold(self) -> None:
        """start_training and start_testing are awaited K times (once per fold)."""
        mock_agent = MagicMock(spec=Agent)
        tasks = [ConcreteTask(name=f"t{i}") for i in range(6)]
        domain = ConcreteDomain(tasks=tasks)
        start_training = AsyncMock()
        start_testing = AsyncMock()
        runner = BenchmarkRunner(
            agent=mock_agent,
            domains=[domain],
            runner=Runner.CROSS_VALIDATION,
            deps_maker=_no_deps_maker,
            cv_n_splits=3,
            start_training=start_training,
            start_testing=start_testing,
        )

        with patch(
            "mcp_evals._internal.runner._cv_runner.tasks_to_dataset",
            side_effect=lambda ts: MagicMock(
                evaluate=AsyncMock(
                    return_value=MagicMock(
                        spec=EvaluationReport,
                        cases=[MagicMock() for _ in range(len(ts))],
                    )
                )
            ),
        ):
            reports = await runner.run()

        assert len(reports) == 1
        assert start_training.await_count == 3
        assert start_testing.await_count == 3


@pytest.mark.asyncio
class TestBenchmarkRunnerSelfCorrection:
    """Tests for BenchmarkRunner with Runner.SELF_CORRECTION."""

    async def test_self_correction_returns_one_report_per_domain(self) -> None:
        """Self-correction runner returns one EvaluationReport per domain."""
        mock_agent = MagicMock(spec=Agent)
        domain = ConcreteDomain(tasks=[ConcreteTask(name=f"t{i}") for i in range(3)])
        runner = BenchmarkRunner(
            agent=mock_agent,
            domains=[domain],
            runner=Runner.SELF_CORRECTION,
            deps_maker=_no_deps_maker,
            max_self_correction_retries=2,
        )
        mock_report = MagicMock(spec=EvaluationReport)
        mock_report.cases = [MagicMock(), MagicMock(), MagicMock()]

        with patch(
            INTERNAL_RUN_SELF_CORRECTION,
            new_callable=AsyncMock,
            return_value=mock_report,
        ):
            reports = await runner.run()

        assert len(reports) == 1
        assert reports[0] is mock_report

    async def test_self_correction_uses_correct_internal_runner(self) -> None:
        """Runner.SELF_CORRECTION creates DomainRunnerSelfCorrection with correct params."""
        mock_agent = MagicMock(spec=Agent)
        domain = ConcreteDomain()
        runner = BenchmarkRunner(
            agent=mock_agent,
            domains=[domain],
            runner=Runner.SELF_CORRECTION,
            deps_maker=_no_deps_maker,
            max_self_correction_retries=5,
        )
        mock_report = MagicMock(spec=EvaluationReport)

        with patch(
            INTERNAL_RUN_SELF_CORRECTION,
            new_callable=AsyncMock,
            return_value=mock_report,
        ) as mock_run:
            await runner.run()
            mock_run.assert_called_once()
            # Verify domain was passed (as keyword)
            assert mock_run.call_args.kwargs["domain"] is domain

    async def test_self_correction_max_tasks_limits_cases(self) -> None:
        """With max_tasks=2, self-correction report contains at most 2 cases."""
        mock_agent = MagicMock(spec=Agent)
        domain = ConcreteDomain(tasks=[ConcreteTask(name=f"t{i}") for i in range(5)])
        runner = BenchmarkRunner(
            agent=mock_agent,
            domains=[domain],
            runner=Runner.SELF_CORRECTION,
            deps_maker=_no_deps_maker,
            max_tasks=2,
        )
        mock_result = MagicMock(spec=AgentRunResult)

        with patch(
            "mcp_evals._internal.runner._self_correction_runner.run_agent_on_task_with_self_correction",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            reports = await runner.run()

        assert len(reports) == 1
        assert len(reports[0].cases) == 2


@pytest.mark.asyncio
class TestRunAgentOnTaskWithSelfCorrection:
    """Tests for run_agent_on_task_with_self_correction evaluated fn."""

    async def test_retries_on_evaluator_failure_and_passes_feedback(self) -> None:
        """When evaluator fails, agent is re-run with augmented goal containing feedback."""

        mock_agent = MagicMock(spec=Agent)
        mock_result = MagicMock(spec=AgentRunResult)
        mock_result.output = MagicMock()
        mock_agent.run = AsyncMock(return_value=mock_result)

        failing_evaluator = AsyncMock(
            side_effect=[
                EvaluationReason(value=0.0, reason="Date order violation"),
                1.0,
            ]
        )

        task = ConcreteTask(name="retry_task")
        task.evaluators = (MagicMock(evaluate=failing_evaluator),)

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
        # Second call: augmented with feedback
        second_goal = mock_agent.run.call_args_list[1].args[0]
        assert "Test goal" in second_goal
        assert "Date order violation" in second_goal
        assert "Fix these issues" in second_goal

    async def test_returns_immediately_when_all_evaluators_pass(self) -> None:
        """When all evaluators pass on first try, no retries occur."""

        mock_agent = MagicMock(spec=Agent)
        mock_result = MagicMock(spec=AgentRunResult)
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
class TestBenchmarkRunnerMaxTasks:
    """Tests for max_tasks limiting the number of tasks run per domain."""

    async def test_inference_only_max_tasks_limits_cases(self) -> None:
        """With max_tasks=2, report contains at most 2 cases (first 2 tasks)."""
        mock_agent = MagicMock(spec=Agent)
        domain = ConcreteDomain(tasks=[ConcreteTask(name=f"t{i}") for i in range(5)])
        runner = BenchmarkRunner(
            agent=mock_agent,
            domains=[domain],
            runner=Runner.INFERENCE_ONLY,
            deps_maker=_no_deps_maker,
            max_tasks=2,
        )
        mock_result = MagicMock(spec=AgentRunResult)

        with patch(
            "mcp_evals._internal.runner._base.run_agent_on_task",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            reports = await runner.run()

        assert len(reports) == 1
        assert len(reports[0].cases) == 2

    async def test_hold_out_max_tasks_limits_task_list(self) -> None:
        """With max_tasks=2, hold_out_split is called with n_tasks=2."""
        mock_agent = MagicMock(spec=Agent)
        domain = ConcreteDomain(tasks=[ConcreteTask(name=f"t{i}") for i in range(5)])
        runner = BenchmarkRunner(
            agent=mock_agent,
            domains=[domain],
            runner=Runner.HOLD_OUT,
            deps_maker=_no_deps_maker,
            max_tasks=2,
            hold_out_test_ratio=0.5,
        )
        call_args: list[tuple[int, float, int | None]] = []

        def capture_hold_out(n_tasks: int, test_ratio: float, random_state: int | None) -> tuple[list[int], list[int]]:
            call_args.append((n_tasks, test_ratio, random_state))
            from mcp_evals._internal.runner._splits import hold_out_split as real  # noqa: PLC0415

            return real(n_tasks, test_ratio, random_state)

        with (
            patch(
                "mcp_evals._internal.runner._hold_out_runner.hold_out_split",
                side_effect=capture_hold_out,
            ),
            patch(
                "mcp_evals._internal.runner._hold_out_runner.tasks_to_dataset",
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
            await runner.run()

        assert len(call_args) == 1
        assert call_args[0][0] == 2

    async def test_cv_max_tasks_limits_task_list(self) -> None:
        """With max_tasks=2, k_fold_split is called with n_tasks=2."""
        mock_agent = MagicMock(spec=Agent)
        domain = ConcreteDomain(tasks=[ConcreteTask(name=f"t{i}") for i in range(5)])
        runner = BenchmarkRunner(
            agent=mock_agent,
            domains=[domain],
            runner=Runner.CROSS_VALIDATION,
            deps_maker=_no_deps_maker,
            max_tasks=2,
            cv_n_splits=2,
        )
        call_args: list[int] = []

        def capture_k_fold(n_tasks: int, n_splits: int, random_state: int | None) -> Any:
            call_args.append(n_tasks)
            from mcp_evals._internal.runner._splits import k_fold_split as real  # noqa: PLC0415

            return real(n_tasks, n_splits, random_state)

        with (
            patch(
                "mcp_evals._internal.runner._cv_runner.k_fold_split",
                side_effect=capture_k_fold,
            ),
            patch(
                "mcp_evals._internal.runner._cv_runner.tasks_to_dataset",
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
            await runner.run()

        assert len(call_args) == 1
        assert call_args[0] == 2
