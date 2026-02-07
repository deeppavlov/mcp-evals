"""Employee hierarchy and customer assignment management in the Chinook database."""

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
# Scalar: 9 employees, 1 CEO, 0 IT Specialist, 4 report to CEO
SCALAR_CHECKS = [
    ('SELECT COUNT(*)::INT FROM "Employee"', 9),
    ('SELECT COUNT(*)::INT FROM "Employee" WHERE "Title" = \'CEO\'', 1),
    ('SELECT COUNT(*)::INT FROM "Employee" WHERE "Title" = \'IT Specialist\'', 0),
    ('SELECT COUNT(*)::INT FROM "Employee" WHERE "ReportsTo" = 1', 4),
]
# Row checks: post-task state — Employee 1 is CEO, Employee 2 is Sales Manager (not pre-task General Manager)
ROW_CHECKS = [
    (
        'SELECT "EmployeeId", "Title", "ReportsTo" FROM "Employee" WHERE "EmployeeId" = 1',
        (1, "CEO", None),
    ),
    (
        'SELECT "EmployeeId", "Title", "ReportsTo" FROM "Employee" WHERE "EmployeeId" = 2',
        (2, "Sales Manager", 1),
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
            HierarchyAndAssignmentScenarioEvaluator(
                required_tables=REQUIRED_TABLES,
                schema="public",
                required_columns=REQUIRED_COLUMNS,
                scalar_checks=SCALAR_CHECKS,
                row_checks=ROW_CHECKS,
            ),
        )
