# ruff: noqa: DTZ001

"""Update employee information in the Chinook database."""

from datetime import datetime

from mcp_evals.contrib.postgres.common_evaluators import SqlResultMatches
from mcp_evals.contrib.postgres.common_evaluators.sql_result_matches import default_rows_match
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

# Expected rows for Employee count and title checks (total_employees, ceo_count, it_specialist_count)
EMPLOYEE_COUNT_QUERY = """
SELECT
    COUNT(*)::int AS total_employees,
    COUNT(CASE WHEN "Title" = 'CEO' THEN 1 END)::int AS ceo_count,
    COUNT(CASE WHEN "Title" = 'IT Specialist' THEN 1 END)::int AS it_specialist_count
FROM "Employee"
"""
EXPECTED_COUNTS = (8, 1, 2)

# Expected rows for EmployeeId 1 and 2 (full row)
EXPECTED_EMPLOYEES_QUERY = """
SELECT "EmployeeId", "LastName", "FirstName", "Title", "ReportsTo", "BirthDate",
       "HireDate", "Address", "City", "State", "Country", "PostalCode",
       "Phone", "Fax", "Email"
FROM "Employee"
WHERE "EmployeeId" IN (1, 2)
ORDER BY "EmployeeId"
"""
EXPECTED_EMPLOYEES_ROWS = [
    # Andrew Adams (ID 1) - Title 'CEO'
    (
        1,
        "Adams",
        "Andrew",
        "CEO",
        None,
        datetime(1962, 2, 18),
        datetime(2002, 8, 14),
        "11120 Jasper Ave NW",
        "Edmonton",
        "AB",
        "Canada",
        "T5K 2N1",
        "+1 (780) 428-9482",
        "+1 (780) 428-3457",
        "andrew@chinookcorp.com",
    ),
    # Nancy Edwards (ID 2) - Phone updated
    (
        2,
        "Edwards",
        "Nancy",
        "Sales Manager",
        1,
        datetime(1958, 12, 8),
        datetime(2002, 5, 1),
        "825 8 Ave SW",
        "Calgary",
        "AB",
        "Canada",
        "T2P 2T3",
        "+1 (403) 555-9999",
        "+1 (403) 262-3322",
        "nancy@chinookcorp.com",
    ),
]


class UpdateEmployeeInfoTask(PostgresTask):
    """Task: update employee info and titles in Chinook."""

    name = "update_employee_info"
    goal = """Update employee information and reorganize the reporting structure \
in the Chinook database to reflect organizational changes.

## Your Tasks

### UPDATE: Modify Existing Employee Information
- Change Andrew Adams (EmployeeId = 1) title from 'General Manager' to 'CEO'
- Update Nancy Edwards (EmployeeId = 2) phone number to '+1 (403) 555-9999'
- Change all employees with Title = 'IT Staff' to have Title = 'IT Specialist'

## Requirements

- Use UPDATE statements to modify the existing records
- The title update for 'IT Staff' should affect all matching employees

## Expected Results

After completing the updates:
- Andrew Adams should have Title = 'CEO'
- Nancy Edwards should have Phone = '+1 (403) 555-9999'
- All employees previously with Title = 'IT Staff' should now have Title = 'IT Specialist'

This task practices UPDATE operations for both employee information and organizational hierarchy management.
"""

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.CHI)
        self.evaluators = (
            SqlResultMatches(
                EMPLOYEE_COUNT_QUERY,
                expected_rows=[EXPECTED_COUNTS],
                rows_match_fn=default_rows_match,
            ),
            SqlResultMatches(
                EXPECTED_EMPLOYEES_QUERY,
                expected_rows=EXPECTED_EMPLOYEES_ROWS,
                rows_match_fn=default_rows_match,
            ),
        )
