"""Employee project tracking in the employees database (mcpmark parity)."""

from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

from .custom_evaluator import EmployeeProjectTrackingScenarioEvaluator


class EmployeeProjectTrackingTask(PostgresTask):
    """Task: create project tracking tables with exact mcpmark spec (tables, data, updates, priority)."""

    name = "employee_project_tracking"

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.EMPL)
        self.evaluators = (EmployeeProjectTrackingScenarioEvaluator(),)
