"""Tests for BenchmarkRunner class."""

from unittest.mock import MagicMock, patch

import pytest
from pydantic_ai.agent import Agent  # type: ignore[import-untyped]
from pydantic_evals.reporting import EvaluationReport  # type: ignore[import-untyped]

from mcp_evals.domain import Domain
from mcp_evals.runner import BenchmarkRunner


class ConcreteDomain(Domain):
    """Concrete Domain implementation for testing."""

    name = "test_domain"

    def __init__(self, name: str = "test_domain") -> None:
        self.name = name

    def mcp_servers(self) -> list:
        """Return empty list of MCP servers."""
        return []

    def tasks(self) -> list:
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

        async def mock_run_domain(domain: Domain, agent: Agent) -> EvaluationReport:  # noqa: ARG001
            call_order.append(domain.name)
            if domain.name == "domain1":
                return mock_report1
            return mock_report2

        with patch("mcp_evals.runner.run_domain", side_effect=mock_run_domain):
            reports = await runner.run()

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
        runner = BenchmarkRunner(agent=mock_agent, domains=[domain1, domain2, domain3])

        mock_reports = [
            MagicMock(spec=EvaluationReport),
            MagicMock(spec=EvaluationReport),
            MagicMock(spec=EvaluationReport),
        ]

        with patch("mcp_evals.runner.run_domain", side_effect=mock_reports):
            reports = await runner.run()

            assert len(reports) == 3
            assert all(isinstance(r, EvaluationReport) for r in reports)
            assert reports[0] is mock_reports[0]
            assert reports[1] is mock_reports[1]
            assert reports[2] is mock_reports[2]

    async def test_handles_empty_domains_list(self) -> None:
        """Test that run() handles empty domains list."""
        mock_agent = MagicMock(spec=Agent)
        runner = BenchmarkRunner(agent=mock_agent, domains=[])

        reports = await runner.run()

        assert isinstance(reports, list)
        assert len(reports) == 0

    async def test_handles_exceptions_in_domain_execution(self) -> None:
        """Test that run() handles exceptions in domain execution."""
        mock_agent = MagicMock(spec=Agent)
        domain1 = ConcreteDomain(name="domain1")
        domain2 = ConcreteDomain(name="domain2")
        runner = BenchmarkRunner(agent=mock_agent, domains=[domain1, domain2])

        mock_report1 = MagicMock(spec=EvaluationReport)

        async def mock_run_domain(domain: Domain, agent: Agent) -> EvaluationReport:  # noqa: ARG001
            if domain.name == "domain1":
                return mock_report1
            raise ValueError("Domain execution failed")

        with (
            patch("mcp_evals.runner.run_domain", side_effect=mock_run_domain),
            pytest.raises(ValueError, match="Domain execution failed"),
        ):
            await runner.run()

    async def test_passes_agent_to_each_domain(self) -> None:
        """Test that run() passes the same agent to each domain."""
        mock_agent = MagicMock(spec=Agent)
        domain1 = ConcreteDomain(name="domain1")
        domain2 = ConcreteDomain(name="domain2")
        runner = BenchmarkRunner(agent=mock_agent, domains=[domain1, domain2])

        received_agents = []

        async def mock_run_domain(domain: Domain, agent: Agent) -> EvaluationReport:  # noqa: ARG001
            received_agents.append(agent)
            return MagicMock(spec=EvaluationReport)

        with patch("mcp_evals.runner.run_domain", side_effect=mock_run_domain):
            await runner.run()

            assert len(received_agents) == 2
            assert all(agent is mock_agent for agent in received_agents)
