"""Employee project tracking: full mcpmark verification (tables, indexes, project/assignment/milestone data)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import psycopg
from psycopg import AsyncCursor
from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.postgres.task import PostgresTask

SCHEMA = "employees"

# Expected final state after all updates (mcpmark verify.py)
EXPECTED_PROJECTS = [
    ("Database Modernization", "2024-01-15", "2024-06-30", 287500.00, "active", "high"),
    ("Employee Portal Upgrade", "2024-02-01", "2024-05-15", 207000.00, "active", "medium"),
    ("HR Analytics Dashboard", "2023-11-01", "2024-01-31", 120000.00, "completed", "medium"),
]

EXPECTED_DEPT_MAPPINGS = {
    "Development": (1, "Developer", 80),
    "Human Resources": (2, "Business Analyst", 60),
    "Marketing": (3, "Marketing Specialist", 40),
    "Finance": (1, "Financial Analyst", 30),
    "Sales": (2, "Sales Representative", 50),
    "Research": (3, "Research Analyst", 70),
    "Production": (1, "Production Coordinator", 45),
    "Quality Management": (2, "QA Specialist", 85),
    "Customer Service": (3, "Customer Success", 35),
}

EXPECTED_MILESTONES = {
    (1, "Design Phase Complete"): ("2024-03-01", False),
    (1, "Implementation Complete"): ("2024-05-15", False),
    (2, "UI/UX Approval"): ("2024-03-15", False),
    (2, "Beta Testing"): ("2024-04-30", False),
    (3, "Data Collection"): ("2023-12-15", True),
    (3, "Dashboard Launch"): ("2024-01-25", False),
}


def _cell_match(actual: object, expected: object) -> bool:
    """Compare one cell; use tolerance for Decimal/float/int; normalize dates to string."""
    if actual == expected:
        return True
    if isinstance(actual, Decimal) and isinstance(expected, (Decimal, float, int)):
        return abs(float(actual) - float(expected)) <= 0.1
    if isinstance(actual, (int, float)) and isinstance(expected, (Decimal, int, float)):
        return abs(float(actual) - float(expected)) <= 0.1
    if hasattr(actual, "strftime"):
        return str(actual) == str(expected)
    return False


def _rows_match(actual_row: tuple[Any, ...], expected_row: tuple[Any, ...]) -> bool:
    """Compare two rows with tolerance for Decimal and date types (mcpmark parity)."""
    if len(actual_row) != len(expected_row):
        return False
    return all(_cell_match(a, e) for a, e in zip(actual_row, expected_row, strict=True))


@dataclass
class EmployeeProjectTrackingScenarioEvaluator(Evaluator["PostgresTask", AgentRunResult]):
    """Verify full mcpmark spec: 3 tables, FKs, indexes, project/assignment/milestone data."""

    schema: str = SCHEMA

    async def evaluate(self, ctx: EvaluatorContext[PostgresTask, AgentRunResult]) -> EvaluatorOutput:
        """Run all mcpmark verification checks."""
        task = ctx.inputs
        params = task.pg_conn_params()
        async with await psycopg.AsyncConnection.connect(**params) as conn, conn.cursor() as cur:
            fail = await _verify_table_structures(cur)
            if fail is not None:
                return fail
            fail = await _verify_indexes(cur)
            if fail is not None:
                return fail
            fail = await _verify_project_data(cur)
            if fail is not None:
                return fail
            fail = await _verify_assignment_data(cur)
            if fail is not None:
                return fail
            fail = await _verify_milestone_data(cur)
            if fail is not None:
                return fail
        return 1.0


async def _verify_table_structures(cur: AsyncCursor) -> EvaluatorOutput | None:
    """Verify 3 tables exist, 3 FKs, priority column on employee_projects."""
    await cur.execute(
        """
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = %s
        AND table_name IN ('employee_projects', 'project_assignments', 'project_milestones')
        ORDER BY table_name
        """,
        (SCHEMA,),
    )
    tables = [r[0] for r in await cur.fetchall()]
    if len(tables) != 3:
        return EvaluationReason(
            value=0.0,
            reason=f"Expected 3 tables (employee_projects, project_assignments, project_milestones), found {len(tables)}: {tables}",
        )

    await cur.execute(
        """
        SELECT COUNT(*) FROM information_schema.table_constraints
        WHERE table_schema = %s
        AND constraint_type = 'FOREIGN KEY'
        AND table_name IN ('project_assignments', 'project_milestones')
        """,
        (SCHEMA,),
    )
    fkey_count = (await cur.fetchone())[0]
    if fkey_count != 3:
        return EvaluationReason(
            value=0.0,
            reason=f"Expected 3 foreign key constraints, found {fkey_count}",
        )

    await cur.execute(
        """
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_schema = %s AND table_name = 'employee_projects' AND column_name = 'priority'
        """,
        (SCHEMA,),
    )
    if (await cur.fetchone())[0] == 0:
        return EvaluationReason(
            value=0.0,
            reason="Priority column was not added to employee_projects table",
        )
    return None


async def _verify_indexes(cur: AsyncCursor) -> EvaluatorOutput | None:
    """Verify idx_projects_status, idx_assignments_emp_proj, idx_milestones_due_date."""
    await cur.execute(
        """
        SELECT COUNT(*) FROM pg_indexes
        WHERE schemaname = %s
        AND indexname IN ('idx_projects_status', 'idx_assignments_emp_proj', 'idx_milestones_due_date')
        """,
        (SCHEMA,),
    )
    index_count = (await cur.fetchone())[0]
    if index_count != 3:
        return EvaluationReason(
            value=0.0,
            reason=f"Expected 3 required indexes (idx_projects_status, idx_assignments_emp_proj, idx_milestones_due_date), got {index_count}",
        )
    return None


async def _verify_project_data(cur: AsyncCursor) -> EvaluatorOutput | None:
    """Verify 3 projects with exact final state after updates."""
    await cur.execute(
        """
        SELECT project_name, start_date, end_date, budget, status, priority
        FROM employees.employee_projects
        ORDER BY project_name
        """
    )
    projects = [tuple(r) for r in await cur.fetchall()]
    if len(projects) != 3:
        return EvaluationReason(
            value=0.0,
            reason=f"Expected 3 projects, found {len(projects)}",
        )
    for i, (project, expected) in enumerate(zip(projects, EXPECTED_PROJECTS, strict=True)):
        if not _rows_match(project, expected):
            return EvaluationReason(
                value=0.0,
                reason=f"Project row {i} mismatch: got {project}, expected {expected}",
            )
    return None


async def _verify_assignment_data(cur: AsyncCursor) -> EvaluatorOutput | None:
    """Verify assignment count = current employee count; department mapping; assigned_date."""
    await cur.execute("SELECT COUNT(*) FROM employees.project_assignments")
    assignment_count = (await cur.fetchone())[0]

    await cur.execute(
        """
        SELECT COUNT(DISTINCT de.employee_id)
        FROM employees.department_employee de
        WHERE de.to_date = '9999-01-01'
        """
    )
    current_employee_count = (await cur.fetchone())[0]

    if assignment_count != current_employee_count:
        return EvaluationReason(
            value=0.0,
            reason=f"Expected {current_employee_count} assignments (one per current employee), found {assignment_count}",
        )

    await cur.execute(
        """
        SELECT d.dept_name, pa.project_id, pa.role, pa.allocation_percentage, COUNT(*)
        FROM employees.project_assignments pa
        JOIN employees.department_employee de ON pa.employee_id = de.employee_id AND de.to_date = '9999-01-01'
        JOIN employees.department d ON de.department_id = d.id
        JOIN employees.employee_projects ep ON pa.project_id = ep.project_id
        GROUP BY d.dept_name, pa.project_id, pa.role, pa.allocation_percentage
        ORDER BY d.dept_name
        """
    )
    dept_assignments = await cur.fetchall()
    dept_found: dict[str, tuple[int, str, int]] = {}
    for row in dept_assignments:
        dept_name, project_id, role, allocation, _ = row
        if dept_name in dept_found:
            return EvaluationReason(
                value=0.0,
                reason=f"Department {dept_name} has multiple assignments",
            )
        dept_found[dept_name] = (project_id, role, allocation)

    for dept, expected in EXPECTED_DEPT_MAPPINGS.items():
        if dept not in dept_found:
            return EvaluationReason(
                value=0.0,
                reason=f"Department {dept} has no assignments",
            )
        if dept_found[dept] != expected:
            return EvaluationReason(
                value=0.0,
                reason=f"Department {dept} assignment mismatch: expected {expected}, got {dept_found[dept]}",
            )

    await cur.execute(
        "SELECT COUNT(*) FROM employees.project_assignments WHERE assigned_date != '2024-01-01'"
    )
    wrong_date_count = (await cur.fetchone())[0]
    if wrong_date_count > 0:
        return EvaluationReason(
            value=0.0,
            reason=f"{wrong_date_count} assignments have incorrect assigned_date (expected 2024-01-01)",
        )
    return None


async def _verify_milestone_data(cur: AsyncCursor) -> EvaluatorOutput | None:
    """Verify 6 milestones with correct due_date and completed (Data Collection = true)."""
    await cur.execute(
        """
        SELECT project_id, milestone_name, due_date, completed
        FROM employees.project_milestones
        ORDER BY project_id, milestone_name
        """
    )
    milestones = [tuple(r) for r in await cur.fetchall()]
    if len(milestones) != 6:
        return EvaluationReason(
            value=0.0,
            reason=f"Expected 6 milestones, found {len(milestones)}",
        )
    for milestone in milestones:
        project_id, name, due_date, completed = milestone
        key = (project_id, name)
        if key not in EXPECTED_MILESTONES:
            return EvaluationReason(
                value=0.0,
                reason=f"Unexpected milestone: {key}",
            )
        expected_due, expected_completed = EXPECTED_MILESTONES[key]
        if str(due_date) != expected_due or completed != expected_completed:
            return EvaluationReason(
                value=0.0,
                reason=f"Milestone {name} mismatch: expected (due={expected_due}, completed={expected_completed}), got (due={due_date}, completed={completed})",
            )
    return None
