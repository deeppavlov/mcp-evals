"""Employee retention analysis in the employees database."""

from mcp_evals.contrib.postgres.common_evaluators import SqlResultMatches
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

# Table or view: retention metrics (e.g. by hire year, still active count)
RETENTION_QUERY = """
SELECT * FROM employees.retention_analysis ORDER BY hire_year
"""
# Ground truth: count of employees by hire year (from employee.hire_date)
RETENTION_EXPECTED = """
SELECT
    EXTRACT(YEAR FROM hire_date)::INT AS hire_year,
    COUNT(*)::BIGINT AS employees_hired
FROM employees.employee
GROUP BY EXTRACT(YEAR FROM hire_date)
ORDER BY hire_year
"""


class EmployeeRetentionAnalysisTask(PostgresTask):
    """Task: create employee retention analysis table or view in employees schema."""

    name = "employee_retention_analysis"

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.EMPL)
        self.evaluators = (
            SqlResultMatches(
                RETENTION_QUERY,
                expected_query=RETENTION_EXPECTED,
            ),
        )
