"""Trigger and procedure for executive dashboard automation in the employees database."""

from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

from .custom_evaluator import TriggerAndProcedureScenarioEvaluator


class ExecutiveDashboardAutomationTask(PostgresTask):
    """Task: create procedure, trigger, and support table for executive dashboard automation."""

    name = "executive_dashboard_automation"
    goal = """Create automation (trigger and procedure) for the executive dashboard in the employees database.

## Your Task

1. Create a **function/procedure** in the **employees** schema (e.g. **log_salary_alert** or **check_salary_alert**)
   that runs when salary data changes and records alerts or summary data.

2. Create a **trigger** (e.g. on employees.salary after INSERT or UPDATE) that calls this procedure.

3. Create a **support table** **employees.salary_alerts** (or similar name) that the procedure writes to,
   with columns such as employee_id, amount, alert_type, created_at, etc.

The evaluator checks that the procedure exists, the trigger exists, and the support table exists. Optionally it may run state checks (e.g. row count) after triggering an update.
"""

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.EMPL)
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
