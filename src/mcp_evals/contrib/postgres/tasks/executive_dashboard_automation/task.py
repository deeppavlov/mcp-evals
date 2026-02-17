"""Trigger and procedure for executive dashboard automation in the employees database."""

from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

from .custom_evaluator import TriggerAndProcedureScenarioEvaluator


class ExecutiveDashboardAutomationTask(PostgresTask):
    """Task: create procedure, trigger, and support table for executive dashboard automation."""

    name = "executive_dashboard_automation"

    def __init__(self, pg_config: PgConfig, tool_retries: int = 1) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.EMPL, tool_retries=tool_retries)
        self.evaluators = (
            TriggerAndProcedureScenarioEvaluator(
                procedure_schema="employees",
                procedure_name="log_salary_alert",
                trigger_schema="employees",
                trigger_name="salary_alert_trigger",
                support_table_schema="employees",
                support_table_name="salary_alerts",
            ),
        )
