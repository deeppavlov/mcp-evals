# ruff: noqa: DTZ001

"""Employee hierarchy and customer assignment management in the Chinook database."""

from datetime import datetime

from mcp_evals.contrib.postgres.common_evaluators import SqlResultMatches
from mcp_evals.contrib.postgres.common_evaluators.sql_result_matches import default_rows_match
from mcp_evals.contrib.postgres.task import PostgresTask
from mcp_evals.contrib.postgres.utils import Backup, PgConfig

from .custom_evaluator import HierarchyAndAssignmentScenarioEvaluator

# Chinook: quoted identifiers, schema public.
# Post-task state (mcpmark parity): insert Sarah/Mike, Adams→CEO, Nancy phone, IT→IT Specialist,
# reassign customers to 9/10, reporting to CEO, create employee_performance, delete Robert King,
# promote Laura, add salary column. So: 9 employees, 1 CEO, 0 IT Specialists, 4 report to CEO.
REQUIRED_TABLES = ["Employee", "Customer", "employee_performance"]
REQUIRED_COLUMNS = [
    ("Employee", ["EmployeeId", "LastName", "FirstName", "Title", "ReportsTo", "salary"]),
    ("Customer", ["CustomerId", "SupportRepId"]),
]
# Scalar: 9 employees, 1 CEO, 0 IT Specialist, 4 report to CEO; customer assignments; deletion; salaries
SCALAR_CHECKS = [
    ('SELECT COUNT(*)::INT FROM "Employee"', 9),
    ('SELECT COUNT(*)::INT FROM "Employee" WHERE "Title" = \'CEO\'', 1),
    ('SELECT COUNT(*)::INT FROM "Employee" WHERE "Title" = \'IT Specialist\'', 0),
    ('SELECT COUNT(*)::INT FROM "Employee" WHERE "ReportsTo" = 1', 4),
    # Customer assignments: 1-3 → 9, 4-6 → 10
    ('SELECT COUNT(*)::INT FROM "Customer" WHERE "CustomerId" IN (1, 2, 3) AND "SupportRepId" = 9', 3),
    ('SELECT COUNT(*)::INT FROM "Customer" WHERE "CustomerId" IN (4, 5, 6) AND "SupportRepId" = 10', 3),
    # Robert King (7) deleted
    ('SELECT COUNT(*)::INT FROM "Employee" WHERE "EmployeeId" = 7', 0),
    # Laura (8) salary 75000; others 50000 (evaluator uses numeric tolerance)
    ('SELECT salary FROM "Employee" WHERE "EmployeeId" = 8', 75000),
    ('SELECT COUNT(*)::INT FROM "Employee" WHERE "EmployeeId" <> 8 AND salary = 50000', 8),
]
# Full 15-column check for employees 1, 2, 9, 10 (mcpmark parity: Nancy phone, addresses, dates, emails)
SPECIFIC_EMPLOYEES_QUERY = """
SELECT "EmployeeId", "LastName", "FirstName", "Title", "ReportsTo", "BirthDate",
       "HireDate", "Address", "City", "State", "Country", "PostalCode",
       "Phone", "Fax", "Email"
FROM "Employee"
WHERE "EmployeeId" IN (1, 2, 9, 10)
ORDER BY "EmployeeId"
"""
EXPECTED_SPECIFIC_EMPLOYEES = [
    # Andrew Adams (ID 1) - CEO, phone stays original, ReportsTo None
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
    # Nancy Edwards (ID 2) - Phone +1 (403) 555-9999, Sales Manager, ReportsTo 1
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
    # Sarah Johnson (9) - all new data, ReportsTo 1
    (
        9,
        "Johnson",
        "Sarah",
        "Sales Support Agent",
        1,
        datetime(1985, 3, 15),
        datetime(2009, 1, 10),
        "123 Oak Street",
        "Calgary",
        "AB",
        "Canada",
        "T2P 5G3",
        "+1 (403) 555-0123",
        "+1 (403) 555-0124",
        "sarah.johnson@chinookcorp.com",
    ),
    # Mike Chen (10) - all new data, ReportsTo 1
    (
        10,
        "Chen",
        "Mike",
        "Sales Support Agent",
        1,
        datetime(1982, 8, 22),
        datetime(2009, 1, 10),
        "456 Pine Ave",
        "Calgary",
        "AB",
        "Canada",
        "T2P 5G4",
        "+1 (403) 555-0125",
        "+1 (403) 555-0126",
        "mike.chen@chinookcorp.com",
    ),
]
# Row checks: Laura (8), employee_performance (1/2 covered by SPECIFIC_EMPLOYEES)
ROW_CHECKS = [
    # Laura: Senior IT Specialist, salary 75000
    (
        'SELECT "EmployeeId", "Title", salary FROM "Employee" WHERE "EmployeeId" = 8',
        (8, "Senior IT Specialist", 75000),
    ),
    # employee_performance: Sarah 3 customers / 4.5, Mike 3 / 4.2
    (
        "SELECT employee_id, customers_assigned, performance_score FROM employee_performance WHERE employee_id = 9",
        (9, 3, 4.5),
    ),
    (
        "SELECT employee_id, customers_assigned, performance_score FROM employee_performance WHERE employee_id = 10",
        (10, 3, 4.2),
    ),
]


class EmployeeHierarchyManagementTask(PostgresTask):
    """Task: manage employee hierarchy and customer assignments (insert/update/delete, employee_performance, salary column)."""

    name = "employee_hierarchy_management"
    goal = """Manage employee hierarchy and customer assignments in the Chinook database.

## Your Task

1. **Insert** two new employees (e.g. Sarah and Mike); **update** the employee who was "General Manager" (e.g. Adams) to Title **'CEO'**; update Nancy's phone as required; change any "IT" title to **'IT Specialist'**; **reassign** customers so that some are assigned to the new employees (SupportRepId 9 and 10), with those employees **reporting to the CEO** (ReportsTo = 1).

2. Create an **employee_performance** table (structure as appropriate for tracking performance).

3. **Delete** employee Robert King.

4. **Promote** Laura as specified (e.g. title or reporting change).

5. Add a **salary** column to the **Employee** table.

6. The evaluator checks the **post-task** state:
   - Total employees: 9
   - Exactly 1 employee with Title **'CEO'** (Employee 1)
   - 0 employees with Title 'IT Specialist' (or equivalent)
   - 4 employees with ReportsTo = 1 (reporting to CEO)
   - Employee 1: Title **'CEO'**, ReportsTo NULL
   - Employee 2: Title **'Sales Manager'**, ReportsTo 1
   - Tables **Employee**, **Customer**, **employee_performance** exist; **Employee** has column **salary**

Use quoted identifiers: "Employee", "Customer", "EmployeeId", "SupportRepId", "Title", "ReportsTo".
"""

    def __init__(self, pg_config: PgConfig) -> None:
        """Init."""
        super().__init__(pg_config=pg_config, category_id=Backup.CHI)
        self.evaluators = (
            SqlResultMatches(
                SPECIFIC_EMPLOYEES_QUERY,
                expected_rows=EXPECTED_SPECIFIC_EMPLOYEES,
                rows_match_fn=default_rows_match,
            ),
            HierarchyAndAssignmentScenarioEvaluator(
                required_tables=REQUIRED_TABLES,
                schema="public",
                required_columns=REQUIRED_COLUMNS,
                scalar_checks=SCALAR_CHECKS,
                row_checks=ROW_CHECKS,
            ),
        )
