"""Tests for BenchmarkRunner class."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai.agent import Agent
from pydantic_ai.mcp import MCPServer
from pydantic_evals.reporting import EvaluationReport

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


class ConcreteDomain(Domain[DomainSecrets]):
    """Concrete Domain implementation for testing."""

    name = "test_domain"

    def __init__(self, name: str = "test_domain") -> None:
        self.name = name

    def mcp_servers(self) -> list[MCPServer]:
        """Return empty list of MCP servers."""
        return []

    def tasks(self) -> list[Task[TaskSecrets, Any]]:
        """Return empty list of tasks."""
        return []


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
