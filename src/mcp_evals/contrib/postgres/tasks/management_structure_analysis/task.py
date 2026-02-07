"""Create manager_profile (and related) in the employees database."""

from mcp_evals.contrib.postgres.common_evaluators import SqlResultMatches
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

# manager_profile: manager periods, current manager, etc. Schema employees.
MANAGER_PROFILE_QUERY = """
SELECT * FROM employees.manager_profile ORDER BY employee_id, from_date
"""
# Ground truth: from department_manager + employee — manager periods per employee/department
MANAGER_PROFILE_EXPECTED = """
SELECT
    dm.employee_id,
    dm.department_id,
    dm.from_date,
    dm.to_date,
    CONCAT(e.first_name, ' ', e.last_name) AS manager_name
FROM employees.department_manager dm
JOIN employees.employee e ON e.id = dm.employee_id
ORDER BY dm.employee_id, dm.from_date
"""


class ManagementStructureAnalysisTask(PostgresTask):
    """Task: create employees.manager_profile for manager periods and current manager info."""

    name = "management_structure_analysis"
    goal = """Create a manager profile table in the employees database for organizational reporting.

## Your Task

Create a table **employees.manager_profile** that describes management structure over time. It should include at least:

- **employee_id** — the manager's employee id (from department_manager)
- **department_id** — department they manage
- **from_date**, **to_date** — period they were/are manager
- **manager_name** — full name (first_name and last_name from employees.employee)

Populate it from employees.department_manager and employees.employee (join on employee id). One row per manager-period. Order by employee_id, from_date for verification.
"""

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.EMPL)
        self.evaluators = (
            SqlResultMatches(
                MANAGER_PROFILE_QUERY,
                expected_query=MANAGER_PROFILE_EXPECTED,
            ),
        )
