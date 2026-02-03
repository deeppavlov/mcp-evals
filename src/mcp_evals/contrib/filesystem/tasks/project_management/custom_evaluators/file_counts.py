"""FileCounts evaluator for project_management task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.project_management.constants import EXPECTED_COUNTS

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.project_management.task import ProjectManagementTask


@dataclass
class FileCounts(Evaluator["ProjectManagementTask", AgentRunResult]):
    """Evaluator that checks each directory has the correct number of files."""

    async def evaluate(self, ctx: EvaluatorContext[ProjectManagementTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that each directory has the correct number of files."""
        task = ctx.inputs
        organized_dir = task.work_dir / "organized_projects"

        incorrect_counts = []
        for dir_path, expected_count in EXPECTED_COUNTS.items():
            full_path = organized_dir / dir_path
            try:
                actual_count = len([f for f in full_path.iterdir() if f.is_file()])

                if actual_count != expected_count:
                    incorrect_counts.append(
                        f"{dir_path}: expected {expected_count}, got {actual_count}",
                    )
            except (OSError, PermissionError):
                incorrect_counts.append(f"{dir_path}: error reading directory")

        if incorrect_counts:
            return EvaluationReason(
                value=0.0,
                reason=f"Incorrect file counts: {incorrect_counts}",
            )

        return 1.0
