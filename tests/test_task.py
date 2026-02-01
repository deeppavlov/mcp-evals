"""Tests for Task class."""

from unittest.mock import MagicMock

import pytest
from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import Evaluator

from mcp_evals.secrets import TaskSecrets
from mcp_evals.task import Task


class ConcreteTask(Task):
    """Concrete Task implementation for testing."""

    name = "test_task"
    goal = "Test goal"
    evaluators: tuple[Evaluator[Task, AgentRunResult], ...] = ()

    def __init__(
        self,
        name: str = "test_task",
        goal: str = "Test goal",
        evaluators: tuple[Evaluator[Task, AgentRunResult], ...] | None = None,
    ) -> None:
        self.name = name
        self.goal = goal
        self.evaluators = evaluators or ()


@pytest.mark.asyncio
class TestTaskContextManager:
    """Tests for Task as async context manager."""

    async def test_aenter_calls_setup(self) -> None:
        """Test that __aenter__ calls setup()."""
        setup_called = []

        class TestTask(ConcreteTask):
            async def setup(self) -> None:
                setup_called.append(True)

        task = TestTask()
        async with task:
            assert len(setup_called) == 1
            assert setup_called[0] is True

    async def test_aexit_calls_teardown(self) -> None:
        """Test that __aexit__ calls teardown()."""
        teardown_called = []

        class TestTask(ConcreteTask):
            async def teardown(self) -> None:
                teardown_called.append(True)

        task = TestTask()
        async with task:
            pass

        assert len(teardown_called) == 1
        assert teardown_called[0] is True

    async def test_multiple_enter_exit_cycles(self) -> None:
        """Test that multiple enter/exit cycles work."""
        setup_calls = []
        teardown_calls = []

        class TestTask(ConcreteTask):
            async def setup(self) -> None:
                setup_calls.append(True)

            async def teardown(self) -> None:
                teardown_calls.append(True)

        task = TestTask()

        # First cycle
        async with task:
            pass

        # Second cycle
        async with task:
            pass

        assert len(setup_calls) == 2
        assert len(teardown_calls) == 2

    async def test_setup_exception_propagates(self) -> None:
        """Test that exceptions in setup() propagate correctly."""

        class TestTask(ConcreteTask):
            async def setup(self) -> None:
                raise ValueError("Setup failed")

        task = TestTask()

        with pytest.raises(ValueError, match="Setup failed"):
            async with task:
                pass

    async def test_teardown_exception_does_not_prevent_exit(self) -> None:
        """Test that exceptions in teardown() don't prevent exit."""
        teardown_called = []

        class TestTask(ConcreteTask):
            async def teardown(self) -> None:
                teardown_called.append(True)
                raise ValueError("Teardown failed")

        task = TestTask()

        # Exception in teardown should be raised, but context should exit
        with pytest.raises(ValueError, match="Teardown failed"):
            async with task:
                pass

        assert len(teardown_called) == 1


@pytest.mark.asyncio
class TestTaskSecrets:
    """Tests for Task secrets functionality."""

    async def test_secrets_property_loads_and_caches(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that secrets property loads and caches secrets."""
        monkeypatch.setenv("TASK_API_KEY", "secret123")

        class MyTaskSecrets(TaskSecrets):
            task_api_key: str

        class TestTask(ConcreteTask):
            secrets_type = MyTaskSecrets

        task = TestTask()

        # First access
        secrets1 = task.secrets
        assert secrets1.task_api_key == "secret123"  # type: ignore[attr-defined]

        # Second access should return same instance (cached)
        secrets2 = task.secrets
        assert secrets1 is secrets2

    async def test_custom_secrets_type_works(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that custom secrets_type works correctly."""
        monkeypatch.setenv("CUSTOM_FIELD", "custom_value")

        class CustomTaskSecrets(TaskSecrets):
            custom_field: str

        class TestTask(ConcreteTask):
            secrets_type = CustomTaskSecrets

        task = TestTask()
        assert task.secrets.custom_field == "custom_value"  # type: ignore[attr-defined]

    async def test_default_secrets_type(self) -> None:
        """Test that default TaskSecrets is used when not specified."""

        class TestTask(ConcreteTask):
            pass

        task = TestTask()
        # Should not raise an error even if no env vars are set
        # (TaskSecrets with no required fields)
        secrets = task.secrets
        assert isinstance(secrets, TaskSecrets)


class TestTaskAttributes:
    """Tests for Task required attributes."""

    def test_task_with_all_attributes(self) -> None:
        """Test that Task with all required attributes works."""
        evaluator = MagicMock(spec=Evaluator)
        task = ConcreteTask(
            name="my_task",
            goal="My goal",
            evaluators=(evaluator,),
        )

        assert task.name == "my_task"
        assert task.goal == "My goal"
        assert len(task.evaluators) == 1

    def test_task_output_type(self) -> None:
        """Test that output_type can be set."""

        class OutputModel:
            pass

        class TestTask(ConcreteTask):
            output_type = OutputModel

        task = TestTask()
        assert task.output_type == OutputModel

    def test_task_output_type_none(self) -> None:
        """Test that output_type defaults to None."""
        task = ConcreteTask()
        assert task.output_type is None


@pytest.mark.asyncio
class TestTaskLifecycle:
    """Tests for Task lifecycle methods."""

    async def test_custom_setup_executes(self) -> None:
        """Test that custom setup logic executes."""
        setup_data = []

        class TestTask(ConcreteTask):
            async def setup(self) -> None:
                setup_data.append("setup_executed")

        task = TestTask()
        async with task:
            assert setup_data == ["setup_executed"]

    async def test_custom_teardown_executes(self) -> None:
        """Test that custom teardown logic executes."""
        teardown_data = []

        class TestTask(ConcreteTask):
            async def teardown(self) -> None:
                teardown_data.append("teardown_executed")

        task = TestTask()
        async with task:
            pass

        assert teardown_data == ["teardown_executed"]

    async def test_setup_and_teardown_order(self) -> None:
        """Test that setup and teardown are called in correct order."""
        call_order = []

        class TestTask(ConcreteTask):
            async def setup(self) -> None:
                call_order.append("setup")

            async def teardown(self) -> None:
                call_order.append("teardown")

        task = TestTask()
        async with task:
            call_order.append("inside_context")

        assert call_order == ["setup", "inside_context", "teardown"]
