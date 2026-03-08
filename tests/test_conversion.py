"""Tests for internal conversion functions."""

from collections.abc import Sequence
from typing import Any
from unittest.mock import MagicMock

from pydantic_ai.mcp import MCPServer
from pydantic_ai.run import AgentRunResult
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import Evaluator

from mcp_evals._internal.conversion import domain_to_dataset
from mcp_evals.domain import Domain
from mcp_evals.secrets import DomainSecrets, TaskSecrets
from mcp_evals.task import Task


class ConcreteTask(Task[TaskSecrets, Any]):
    """Concrete Task implementation for testing."""

    name = "test_task"
    goal = "Test goal"
    evaluators: tuple[Evaluator[Task[TaskSecrets, Any], AgentRunResult], ...] = ()

    def __init__(
        self,
        name: str = "test_task",
        goal: str = "Test goal",
        evaluators: tuple[Evaluator[Task[TaskSecrets, Any], AgentRunResult], ...] | None = None,
        tool_retries: int = 1,
    ) -> None:
        super().__init__(tool_retries=tool_retries)
        self.name = name
        self.goal = goal
        self.evaluators = evaluators or ()


class ConcreteDomain(Domain[DomainSecrets]):
    """Concrete Domain implementation for testing."""

    name = "test_domain"

    def __init__(self, tasks: list[ConcreteTask] | None = None, tool_retries: int = 1) -> None:
        super().__init__(tool_retries=tool_retries)
        self._tasks = tasks or []

    def mcp_servers(self) -> Sequence[MCPServer]:
        """Return empty list of MCP servers."""
        return []

    def _tasks_impl(self) -> Sequence[ConcreteTask]:
        """Return tasks."""
        return self._tasks


class TestDomainToDataset:
    """Tests for domain_to_dataset conversion function."""

    def test_converts_domain_to_dataset(self) -> None:
        """Test that domain_to_dataset converts Domain to Dataset correctly."""
        task1 = ConcreteTask(name="task1", goal="Goal 1")
        task2 = ConcreteTask(name="task2", goal="Goal 2")
        domain = ConcreteDomain(tasks=[task1, task2])

        dataset = domain_to_dataset(domain)

        assert isinstance(dataset, Dataset)
        assert len(dataset.cases) == 2

    def test_each_task_becomes_case_with_correct_name(self) -> None:
        """Test that each Task becomes a Case with correct name."""
        task1 = ConcreteTask(name="task1", goal="Goal 1")
        task2 = ConcreteTask(name="task2", goal="Goal 2")
        domain = ConcreteDomain(tasks=[task1, task2])

        dataset = domain_to_dataset(domain)

        case_names = [case.name for case in dataset.cases]
        assert "task1" in case_names
        assert "task2" in case_names

    def test_task_instance_passed_as_inputs(self) -> None:
        """Test that Task instance is passed as inputs."""
        task = ConcreteTask(name="test_task", goal="Test goal")
        domain = ConcreteDomain(tasks=[task])

        dataset = domain_to_dataset(domain)

        assert len(dataset.cases) == 1
        case = dataset.cases[0]
        assert case.inputs is task
        assert case.inputs.name == "test_task"
        assert case.inputs.goal == "Test goal"

    def test_evaluators_correctly_assigned(self) -> None:
        """Test that evaluators are correctly assigned to cases."""
        evaluator1 = MagicMock(spec=Evaluator)
        evaluator2 = MagicMock(spec=Evaluator)
        task = ConcreteTask(
            name="test_task",
            goal="Test goal",
            evaluators=(evaluator1, evaluator2),
        )
        domain = ConcreteDomain(tasks=[task])

        dataset = domain_to_dataset(domain)

        assert len(dataset.cases) == 1
        case = dataset.cases[0]
        assert len(case.evaluators) == 2
        assert evaluator1 in case.evaluators
        assert evaluator2 in case.evaluators

    def test_empty_tasks_list_creates_empty_dataset(self) -> None:
        """Test that empty tasks list creates empty dataset."""
        domain = ConcreteDomain(tasks=[])

        dataset = domain_to_dataset(domain)

        assert isinstance(dataset, Dataset)
        assert len(dataset.cases) == 0

    def test_multiple_tasks_create_multiple_cases(self) -> None:
        """Test that multiple tasks create multiple cases."""
        tasks = [ConcreteTask(name=f"task{i}", goal=f"Goal {i}") for i in range(5)]
        domain = ConcreteDomain(tasks=tasks)

        dataset = domain_to_dataset(domain)

        assert len(dataset.cases) == 5
        for i, case in enumerate(dataset.cases):
            assert case.name == f"task{i}"
            assert case.inputs.goal == f"Goal {i}"

    def test_preserves_task_attributes(self) -> None:
        """Test that task attributes are preserved in case inputs."""
        task = ConcreteTask(
            name="custom_task",
            goal="Custom goal",
            evaluators=(),
        )
        # Add custom attribute
        task.custom_attr = "custom_value"  # type: ignore[attr-defined]

        domain = ConcreteDomain(tasks=[task])
        dataset = domain_to_dataset(domain)

        case = dataset.cases[0]
        assert hasattr(case.inputs, "custom_attr")
        assert case.inputs.custom_attr == "custom_value"

    def test_case_types_are_correct(self) -> None:
        """Test that Case types are correct."""
        task = ConcreteTask(name="test_task", goal="Test goal")
        domain = ConcreteDomain(tasks=[task])

        dataset = domain_to_dataset(domain)

        case = dataset.cases[0]
        assert isinstance(case, Case)
        assert isinstance(case.inputs, Task)
        assert case.inputs is task
