"""Create demographics report tables in the employees database (mcpmark parity: full columns)."""

from mcp_evals.contrib.postgres.common_evaluators import SqlResultMatches
from mcp_evals.contrib.postgres.common_evaluators.sql_result_matches import default_rows_match
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

# Current employees: have a salary row with to_date = '9999-01-01'
# Schema: employees.employee (id, birth_date, hire_date, gender), employees.salary (employee_id, to_date, amount)

# 1. gender_statistics: total_employees, current_employees, percentage_of_workforce
GENDER_STATISTICS_QUERY = """
SELECT * FROM employees.gender_statistics ORDER BY gender
"""
GENDER_STATISTICS_EXPECTED = """
WITH current_emp AS (
    SELECT DISTINCT employee_id FROM employees.salary WHERE to_date = DATE '9999-01-01'
),
by_gender AS (
    SELECT
        e.gender,
        COUNT(*)::BIGINT AS total_employees,
        COUNT(*) FILTER (WHERE ce.employee_id IS NOT NULL)::BIGINT AS current_employees
    FROM employees.employee e
    LEFT JOIN current_emp ce ON ce.employee_id = e.id
    GROUP BY e.gender
),
totals AS (
    SELECT SUM(current_employees) AS t FROM by_gender
)
SELECT
    g.gender,
    g.total_employees,
    g.current_employees,
    ROUND(100.0 * g.current_employees / NULLIF(t.t, 0), 2)::DECIMAL AS percentage_of_workforce
FROM by_gender g
CROSS JOIN totals t
ORDER BY g.gender
"""

# 2. age_group_analysis: age groups 20-29, 30-39, 40-49, 50-59, 60+; employee_count, avg_salary, avg_tenure_days
AGE_GROUP_QUERY = """
SELECT * FROM employees.age_group_analysis ORDER BY age_group
"""
AGE_GROUP_EXPECTED = """
WITH current_sal AS (
    SELECT DISTINCT ON (employee_id) employee_id, amount
    FROM employees.salary WHERE to_date = DATE '9999-01-01'
    ORDER BY employee_id, from_date DESC
),
ages AS (
    SELECT
        e.id,
        CASE
            WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, e.birth_date)) < 20 THEN 'under_20'
            WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, e.birth_date)) < 30 THEN '20-29'
            WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, e.birth_date)) < 40 THEN '30-39'
            WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, e.birth_date)) < 50 THEN '40-49'
            WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, e.birth_date)) < 60 THEN '50-59'
            ELSE '60+'
        END AS age_group,
        cs.amount AS salary,
        (CURRENT_DATE - e.hire_date)::INT AS tenure_days
    FROM employees.employee e
    INNER JOIN current_sal cs ON cs.employee_id = e.id
)
SELECT
    age_group,
    COUNT(*)::BIGINT AS employee_count,
    ROUND(AVG(salary), 2)::DECIMAL AS avg_salary,
    ROUND(AVG(tenure_days))::BIGINT AS avg_tenure_days
FROM ages
GROUP BY age_group
ORDER BY age_group
"""

# 3. birth_month_distribution: month_name, employee_count, current_employee_count
BIRTH_MONTH_QUERY = """
SELECT * FROM employees.birth_month_distribution ORDER BY 1
"""
BIRTH_MONTH_EXPECTED = """
WITH current_emp AS (
    SELECT DISTINCT employee_id FROM employees.salary WHERE to_date = DATE '9999-01-01'
),
months AS (
    SELECT 1 AS birth_month, 'January' AS month_name UNION ALL SELECT 2, 'February' UNION ALL SELECT 3, 'March'
    UNION ALL SELECT 4, 'April' UNION ALL SELECT 5, 'May' UNION ALL SELECT 6, 'June'
    UNION ALL SELECT 7, 'July' UNION ALL SELECT 8, 'August' UNION ALL SELECT 9, 'September'
    UNION ALL SELECT 10, 'October' UNION ALL SELECT 11, 'November' UNION ALL SELECT 12, 'December'
)
SELECT
    m.birth_month,
    m.month_name,
    COUNT(e.id)::BIGINT AS employee_count,
    COUNT(ce.employee_id)::BIGINT AS current_employee_count
FROM months m
LEFT JOIN employees.employee e ON EXTRACT(MONTH FROM e.birth_date) = m.birth_month
LEFT JOIN current_emp ce ON ce.employee_id = e.id
GROUP BY m.birth_month, m.month_name
ORDER BY m.birth_month
"""

# 4. hiring_year_summary: employees_hired, still_employed, retention_rate
HIRING_YEAR_QUERY = """
SELECT * FROM employees.hiring_year_summary ORDER BY hire_year
"""
HIRING_YEAR_EXPECTED = """
WITH hire_years AS (
    SELECT
        EXTRACT(YEAR FROM hire_date)::INT AS hire_year,
        id
    FROM employees.employee
),
current_emp AS (
    SELECT DISTINCT employee_id FROM employees.salary WHERE to_date = DATE '9999-01-01'
)
SELECT
    h.hire_year,
    COUNT(h.id)::BIGINT AS employees_hired,
    COUNT(ce.employee_id)::BIGINT AS still_employed,
    ROUND(100.0 * COUNT(ce.employee_id) / NULLIF(COUNT(h.id), 0), 2)::DECIMAL AS retention_rate
FROM (SELECT DISTINCT hire_year FROM hire_years) y
JOIN hire_years h ON h.hire_year = y.hire_year
LEFT JOIN current_emp ce ON ce.employee_id = h.id
GROUP BY h.hire_year
ORDER BY h.hire_year
"""


class EmployeeDemographicsReportTask(PostgresTask):
    """Task: create full demographics report tables (mcpmark parity: current, %, retention)."""

    name = "employee_demographics_report"
    goal = """Create demographic report tables in the employees database for HR analytics (full mcpmark-style columns).

## Your Task

Create the following tables in the **employees** schema. Use **current** employees where relevant: those with a row in \
**employees.salary** where **to_date = DATE '9999-01-01'**.

1. **gender_statistics** — One row per gender with:
   - **gender** — M/F (or as in employees.employee)
   - **total_employees** — count of all employees (from employees.employee)
   - **current_employees** — count of current employees (in salary with to_date = '9999-01-01')
   - **percentage_of_workforce** — 100 * current_employees / total_current (decimal, e.g. 2 decimal places)

2. **age_group_analysis** — One row per age bucket (use **current** employees only for counts and averages):
   - **age_group** — 'under_20', '20-29', '30-39', '40-49', '50-59', '60+'
   - **employee_count** — count of current employees in that age group
   - **avg_salary** — average current salary (from employees.salary to_date = '9999-01-01')
   - **avg_tenure_days** — average tenure in days (CURRENT_DATE - hire_date)

3. **birth_month_distribution** — One row per month (1-12):
   - **month_num** (or equivalent) and **month_name** (e.g. 'January', 'February')
   - **employee_count** — total employees born in that month
   - **current_employee_count** — current employees born in that month

4. **hiring_year_summary** — One row per hire year:
   - **hire_year** — year from employees.employee.hire_date
   - **employees_hired** — count hired in that year
   - **still_employed** — count of those still current (in salary to_date = '9999-01-01')
   - **retention_rate** — 100 * still_employed / employees_hired (decimal)

Use employees.employee, employees.salary. Order by the key column (gender, age_group, month_num, hire_year) for \
verification. The evaluator uses decimal tolerance for numeric columns.
"""

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.EMPL)
        self.evaluators = (
            SqlResultMatches(
                GENDER_STATISTICS_QUERY,
                expected_query=GENDER_STATISTICS_EXPECTED,
                rows_match_fn=default_rows_match,
            ),
            SqlResultMatches(
                AGE_GROUP_QUERY,
                expected_query=AGE_GROUP_EXPECTED,
                rows_match_fn=default_rows_match,
            ),
            SqlResultMatches(
                BIRTH_MONTH_QUERY,
                expected_query=BIRTH_MONTH_EXPECTED,
                rows_match_fn=default_rows_match,
            ),
            SqlResultMatches(
                HIRING_YEAR_QUERY,
                expected_query=HIRING_YEAR_EXPECTED,
                rows_match_fn=default_rows_match,
            ),
        )
