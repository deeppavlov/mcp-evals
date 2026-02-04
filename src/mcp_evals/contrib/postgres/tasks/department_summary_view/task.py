"""Create exec_department_summary materialized view in the employees database."""

from mcp_evals.contrib.postgres.common_evaluators import SqlResultMatches
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import PgConfig

# Query that selects from the materialized view (what the agent should create)
VIEW_QUERY = """
SELECT department_name, total_employees, avg_salary, total_payroll, manager_name
FROM employees.exec_department_summary
ORDER BY department_name
"""

# Ground truth: same logic as mcpmark verify - compute expected result from base tables
EXPECTED_QUERY = """
WITH current_salary AS (
    SELECT employee_id, amount
    FROM (
        SELECT s.*,
            ROW_NUMBER() OVER (
                PARTITION BY s.employee_id
                ORDER BY s.from_date DESC, s.amount DESC
            ) AS rn
        FROM employees.salary s
        WHERE s.to_date = DATE '9999-01-01'
    ) x
    WHERE rn = 1
),
current_dept AS (
    SELECT DISTINCT de.employee_id, de.department_id
    FROM employees.department_employee de
    WHERE de.to_date = DATE '9999-01-01'
),
current_manager AS (
    SELECT department_id,
            CONCAT(e.first_name, ' ', e.last_name) AS manager_name
    FROM (
        SELECT dm.*,
            ROW_NUMBER() OVER (
                PARTITION BY dm.department_id
                ORDER BY dm.from_date DESC, dm.employee_id
            ) AS rn
        FROM employees.department_manager dm
        WHERE dm.to_date = DATE '9999-01-01'
    ) dm
    JOIN employees.employee e ON e.id = dm.employee_id
    WHERE dm.rn = 1
)
SELECT
    d.dept_name AS department_name,
    COUNT(cd.employee_id)::INT AS total_employees,
    AVG(cs.amount)::DECIMAL AS avg_salary,
    COALESCE(SUM(cs.amount), 0)::BIGINT AS total_payroll,
    cm.manager_name
FROM employees.department d
LEFT JOIN current_dept cd ON cd.department_id = d.id
LEFT JOIN current_salary cs ON cs.employee_id = cd.employee_id
LEFT JOIN current_manager cm ON cm.department_id = d.id
GROUP BY d.id, d.dept_name, cm.manager_name
ORDER BY d.dept_name
"""


class DepartmentSummaryViewTask(PostgresTask):
    """Task: create exec_department_summary materialized view in employees schema."""

    name = "department_summary_view"
    goal = """Create an executive department summary view to provide quick insights into departmental \
metrics for leadership dashboards. This view will consolidate key department statistics in one easily accessible place.

## Your Task

**Create the executive department summary view** — build a materialized view called `exec_department_summary` in the \
`employees` schema with these exact columns:

* `department_name` (varchar) — department name
* `total_employees` (integer) — current active employee count (employees with active salary where to_date = \
'9999-01-01')
* `avg_salary` (decimal) — average current salary for active employees
* `total_payroll` (bigint) — total monthly payroll cost (sum of all current salaries in the department)
* `manager_name` (varchar) — current department manager's full name (first_name and last_name concatenated)

## Requirements

1. Use materialized view to cache results for better performance
2. Join the following tables:
   - `departments` - for department information
   - `dept_emp` - for employee-department relationships
   - `employees` - for employee details
   - `salaries` - for current salary information
   - `dept_manager` - for current manager information
3. Only include current active employees (those with to_date = '9999-01-01' in both `dept_emp` and `salaries`)
4. Only include current managers (to_date = '9999-01-01' in `dept_manager`)
5. Order results by department_name

## After Creation

Refresh the materialized view to populate it with current data.

This view will provide executives with a real-time snapshot of departmental workforce metrics and costs.
"""

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id="employees")
        self.evaluators = (
            SqlResultMatches(
                VIEW_QUERY,
                expected_query=EXPECTED_QUERY,
            ),
        )
