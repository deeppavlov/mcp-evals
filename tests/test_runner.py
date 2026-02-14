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


@asynccontextmanager
async def _yield_none_cm() -> AsyncGenerator[None]:
    yield None


def _no_deps_maker(_task: Task[TaskSecrets, Any]) -> Any:
    """Deps maker that yields None (for tests that don't need real deps)."""
    return _yield_none_cm()


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

        runner = BenchmarkRunner(agent=mock_agent, domains=[domain1, domain2])

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
        runner = BenchmarkRunner(agent=mock_agent, domains=[domain1, domain2])

        mock_report1 = MagicMock(spec=EvaluationReport)
        mock_report2 = MagicMock(spec=EvaluationReport)

        call_order = []

        async def mock_run_domain(
            domain: Domain[DomainSecrets],
            agent: Agent,  # noqa: ARG001
            *,
            experiment_name: str | None = None,  # noqa: ARG001
            deps_maker: Any = None,  # noqa: ARG001
        ) -> EvaluationReport:
            call_order.append(domain.name)
            if domain.name == "domain1":
                return mock_report1
            return mock_report2

        with patch("mcp_evals.runner.run_domain", side_effect=mock_run_domain):
            reports = await runner.run(deps_maker=_no_deps_maker, experiment_name=None)

            assert len(reports) == 2
            assert reports[0] is mock_report1
            assert reports[1] is mock_report2
            assert call_order == ["domain1", "domain2"]

    async def test_returns_list_of_evaluation_reports(self) -> None:
        """Test that run() returns list of EvaluationReport."""
        mock_agent = MagicMock(spec=Agent)
        domain = ConcreteDomain()
        runner = BenchmarkRunner(agent=mock_agent, domains=[domain])

        mock_report = MagicMock(spec=EvaluationReport)

        with patch("mcp_evals.runner.run_domain", return_value=mock_report):
            reports = await runner.run(deps_maker=_no_deps_maker, experiment_name=None)

            assert isinstance(reports, list)
            assert len(reports) == 1
            assert reports[0] is mock_report

    async def test_each_domain_gets_own_report(self) -> None:
        """Test that each domain gets its own report."""
        mock_agent = MagicMock(spec=Agent)
        domain1 = ConcreteDomain(name="domain1")
        domain2 = ConcreteDomain(name="domain2")
        domain3 = ConcreteDomain(name="domain3")
        runner = BenchmarkRunner(agent=mock_agent, domains=[domain1, domain2, domain3])

        mock_reports = [
            MagicMock(spec=EvaluationReport),
            MagicMock(spec=EvaluationReport),
            MagicMock(spec=EvaluationReport),
        ]

        with patch("mcp_evals.runner.run_domain", side_effect=mock_reports):
            reports = await runner.run(deps_maker=_no_deps_maker, experiment_name=None)

            assert len(reports) == 3
            assert all(isinstance(r, EvaluationReport) for r in reports)
            assert reports[0] is mock_reports[0]
            assert reports[1] is mock_reports[1]
            assert reports[2] is mock_reports[2]

    async def test_handles_empty_domains_list(self) -> None:
        """Test that run() handles empty domains list."""
        mock_agent = MagicMock(spec=Agent)
        runner = BenchmarkRunner(agent=mock_agent, domains=[])

        reports = await runner.run(experiment_name=None)

        assert isinstance(reports, list)
        assert len(reports) == 0

    async def test_handles_exceptions_in_domain_execution(self) -> None:
        """Test that run() handles exceptions in domain execution."""
        mock_agent = MagicMock(spec=Agent)
        domain1 = ConcreteDomain(name="domain1")
        domain2 = ConcreteDomain(name="domain2")
        runner = BenchmarkRunner(agent=mock_agent, domains=[domain1, domain2])

        mock_report1 = MagicMock(spec=EvaluationReport)

        async def mock_run_domain(
            domain: Domain[DomainSecrets],
            agent: Agent,  # noqa: ARG001
            *,
            experiment_name: str | None = None,  # noqa: ARG001
            deps_maker: Any = None,  # noqa: ARG001
        ) -> EvaluationReport:
            if domain.name == "domain1":
                return mock_report1
            raise ValueError("Domain execution failed")

        with (
            patch("mcp_evals.runner.run_domain", side_effect=mock_run_domain),
            pytest.raises(ValueError, match="Domain execution failed"),
        ):
            await runner.run(deps_maker=_no_deps_maker, experiment_name=None)

    async def test_passes_agent_to_each_domain(self) -> None:
        """Test that run() passes the same agent to each domain."""
        mock_agent = MagicMock(spec=Agent)
        domain1 = ConcreteDomain(name="domain1")
        domain2 = ConcreteDomain(name="domain2")
        runner = BenchmarkRunner(agent=mock_agent, domains=[domain1, domain2])

        received_agents = []

        async def mock_run_domain(
            domain: Domain[DomainSecrets],  # noqa: ARG001
            agent: Agent,
            *,
            experiment_name: str | None = None,  # noqa: ARG001
            deps_maker: Any = None,  # noqa: ARG001
        ) -> EvaluationReport:
            received_agents.append(agent)
            return MagicMock(spec=EvaluationReport)

        with patch("mcp_evals.runner.run_domain", side_effect=mock_run_domain):
            await runner.run(deps_maker=_no_deps_maker, experiment_name=None)

            assert len(received_agents) == 2
            assert all(agent is mock_agent for agent in received_agents)

    async def test_run_without_deps_maker_calls_run_domain_with_none(self) -> None:
        """Test that run() without deps_maker calls run_domain with deps_maker=None."""
        mock_agent = MagicMock(spec=Agent)
        domain = ConcreteDomain()
        runner = BenchmarkRunner(agent=mock_agent, domains=[domain])

        with patch("mcp_evals.runner.run_domain", new_callable=AsyncMock) as mock_run_domain:
            mock_run_domain.return_value = MagicMock(spec=EvaluationReport)
            await runner.run(experiment_name="exp")

            mock_run_domain.assert_called_once_with(domain, mock_agent, experiment_name="exp", deps_maker=None)

    async def test_passes_deps_maker_to_run_domain(self) -> None:
        """Test that run(deps_maker=...) forwards deps_maker to run_domain."""
        mock_agent = MagicMock(spec=Agent)
        domain = ConcreteDomain()
        runner = BenchmarkRunner(agent=mock_agent, domains=[domain])
        custom_factory = _no_deps_maker

        with patch("mcp_evals.runner.run_domain", new_callable=AsyncMock) as mock_run_domain:
            mock_run_domain.return_value = MagicMock(spec=EvaluationReport)
            await runner.run(deps_maker=custom_factory, experiment_name=None)

            mock_run_domain.assert_called_once_with(domain, mock_agent, experiment_name=None, deps_maker=custom_factory)
