"""Create demographics report tables in the employees database."""

from mcp_evals.contrib.postgres.common_evaluators import SqlResultMatches
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

# Schema: employees
# Four tables: gender_statistics, age_group_analysis, birth_month_distribution, hiring_year_summary

GENDER_STATISTICS_QUERY = """
SELECT * FROM employees.gender_statistics ORDER BY gender
"""
GENDER_STATISTICS_EXPECTED = """
SELECT gender, COUNT(*)::BIGINT AS count
FROM employees.employee
GROUP BY gender
ORDER BY gender
"""

AGE_GROUP_QUERY = """
SELECT * FROM employees.age_group_analysis ORDER BY age_group
"""
AGE_GROUP_EXPECTED = """
WITH ages AS (
    SELECT
        id,
        CASE
            WHEN EXTRACT(YEAR FROM AGE(birth_date)) < 30 THEN 'under_30'
            WHEN EXTRACT(YEAR FROM AGE(birth_date)) < 50 THEN '30_to_50'
            ELSE 'over_50'
        END AS age_group
    FROM employees.employee
)
SELECT age_group, COUNT(*)::BIGINT AS count
FROM ages
GROUP BY age_group
ORDER BY age_group
"""

BIRTH_MONTH_QUERY = """
SELECT * FROM employees.birth_month_distribution ORDER BY birth_month
"""
BIRTH_MONTH_EXPECTED = """
SELECT
    EXTRACT(MONTH FROM birth_date)::INT AS birth_month,
    COUNT(*)::BIGINT AS count
FROM employees.employee
GROUP BY EXTRACT(MONTH FROM birth_date)
ORDER BY birth_month
"""

HIRING_YEAR_QUERY = """
SELECT * FROM employees.hiring_year_summary ORDER BY hire_year
"""
HIRING_YEAR_EXPECTED = """
SELECT
    EXTRACT(YEAR FROM hire_date)::INT AS hire_year,
    COUNT(*)::BIGINT AS count
FROM employees.employee
GROUP BY EXTRACT(YEAR FROM hire_date)
ORDER BY hire_year
"""


class EmployeeDemographicsReportTask(PostgresTask):
    """Task: create gender_statistics, age_group_analysis, birth_month_distribution, hiring_year_summary in employees schema."""

    name = "employee_demographics_report"
    goal = """Create demographic report tables in the employees database for HR analytics.

## Your Task

Create the following tables in the **employees** schema (employees.gender_statistics, etc.):

1. **gender_statistics** — One row per gender with a count of employees (columns e.g. gender, count). Source: employees.employee.

2. **age_group_analysis** — Bucket employees by age (e.g. under_30, 30_to_50, over_50) based on birth_date and store age_group and count. Use CURRENT_DATE for age.

3. **birth_month_distribution** — Month of birth (1–12) and count of employees (columns e.g. birth_month, count).

4. **hiring_year_summary** — Year of hire and count of employees (columns e.g. hire_year, count).

Use the existing table employees.employee (columns include id, birth_date, hire_date, gender). Populate each table with the correct aggregates. Column names may vary slightly but must support ordering for verification (e.g. gender, age_group, birth_month, hire_year plus count).
"""

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.EMPL)
        self.evaluators = (
            SqlResultMatches(GENDER_STATISTICS_QUERY, expected_query=GENDER_STATISTICS_EXPECTED),
            SqlResultMatches(AGE_GROUP_QUERY, expected_query=AGE_GROUP_EXPECTED),
            SqlResultMatches(BIRTH_MONTH_QUERY, expected_query=BIRTH_MONTH_EXPECTED),
            SqlResultMatches(HIRING_YEAR_QUERY, expected_query=HIRING_YEAR_EXPECTED),
        )
