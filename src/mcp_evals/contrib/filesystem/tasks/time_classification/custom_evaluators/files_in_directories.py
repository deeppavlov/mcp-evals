"""FilesInDirectories evaluator for time_classification task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.time_classification.constants import EXPECTED_STRUCTURE, SYSTEM_FILES
from mcp_evals.contrib.filesystem.tasks.time_classification.task import find_day_directory, find_month_directory

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.time_classification.task import TimeClassificationTask


@dataclass
class FilesInDirectories(Evaluator["TimeClassificationTask", AgentRunResult]):
    """Evaluator that checks files are in the correct directories."""

    async def evaluate(self, ctx: EvaluatorContext[TimeClassificationTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that files are in the correct directories."""
        task = ctx.inputs

        for expected_month, days in EXPECTED_STRUCTURE.items():
            month_dir = find_month_directory(task.work_dir, expected_month)
            if month_dir is None:
                continue  # Already handled in DirectoryStructure

            for day, expected_files in days.items():
                day_dir = find_day_directory(month_dir, day)
                if day_dir is None:
                    continue  # Already handled in DirectoryStructure

                missing_files = []
                for filename in expected_files:
                    file_path = day_dir / filename
                    if not file_path.exists():
                        missing_files.append(filename)

                if missing_files:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Missing files in '{month_dir.name}/{day_dir.name}': {missing_files}",
                    )

                try:
                    actual_files = [f.name for f in day_dir.iterdir() if f.is_file()]
                    unexpected_files = [f for f in actual_files if f not in expected_files and f not in SYSTEM_FILES]

                    if unexpected_files:
                        msg = f"Unexpected files in '{month_dir.name}/{day_dir.name}': {unexpected_files}"
                        return EvaluationReason(value=0.0, reason=msg)
                except (OSError, PermissionError) as e:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Error reading directory '{month_dir.name}/{day_dir.name}': {e}",
                    )

        return 1.0
