"""Employee performance analysis in the employees database."""

from mcp_evals.contrib.postgres.common_evaluators import SqlResultMatches
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

# Table or view: employee performance metrics (e.g. tenure, salary growth, department)
EMPLOYEE_PERFORMANCE_QUERY = """
SELECT * FROM employees.employee_performance ORDER BY employee_id
"""
# Ground truth: current salary and tenure from employees/salary/department_employee
EMPLOYEE_PERFORMANCE_EXPECTED = """
WITH current_sal AS (
    SELECT DISTINCT ON (employee_id) employee_id, amount
    FROM employees.salary
    ORDER BY employee_id, from_date DESC
),
current_dept AS (
    SELECT DISTINCT ON (employee_id) employee_id, department_id
    FROM employees.department_employee
    WHERE to_date = DATE '9999-01-01'
    ORDER BY employee_id, from_date DESC
)
SELECT
    e.id AS employee_id,
    e.hire_date,
    EXTRACT(YEAR FROM AGE(CURRENT_DATE, e.hire_date))::INT AS tenure_years,
    cs.amount AS current_salary,
    cd.department_id
FROM employees.employee e
LEFT JOIN current_sal cs ON cs.employee_id = e.id
LEFT JOIN current_dept cd ON cd.employee_id = e.id
ORDER BY e.id
"""


class EmployeePerformanceAnalysisTask(PostgresTask):
    """Task: create employee performance analysis table or view in employees schema."""

    name = "employee_performance_analysis"

    def __init__(self, pg_config: PgConfig, tool_retries: int = 1) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.EMPL, tool_retries=tool_retries)
        self.evaluators = (
            SqlResultMatches(
                EMPLOYEE_PERFORMANCE_QUERY,
                expected_query=EMPLOYEE_PERFORMANCE_EXPECTED,
            ),
        )
