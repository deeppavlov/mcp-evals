"""MetadataAnalysisFiles evaluator for time_classification task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.time_classification.constants import EXPECTED_STRUCTURE
from mcp_evals.contrib.filesystem.tasks.time_classification.task import (
    _validate_metadata_line,
    find_day_directory,
    find_month_directory,
)

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.time_classification.task import TimeClassificationTask


@dataclass
class MetadataAnalysisFiles(Evaluator["TimeClassificationTask", AgentRunResult]):
    """Evaluator that checks metadata_analyse.txt files exist and have correct content."""

    async def evaluate(self, ctx: EvaluatorContext[TimeClassificationTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that metadata_analyse.txt files exist and have correct content."""
        task = ctx.inputs

        for expected_month, days in EXPECTED_STRUCTURE.items():
            month_dir = find_month_directory(task.work_dir, expected_month)
            if month_dir is None:
                continue  # Already handled in DirectoryStructure

            for day in days:
                day_dir = find_day_directory(month_dir, day)
                if day_dir is None:
                    continue  # Already handled in DirectoryStructure

                metadata_file = day_dir / "metadata_analyse.txt"

                if not metadata_file.exists():
                    return EvaluationReason(
                        value=0.0,
                        reason=f"metadata_analyse.txt not found in '{month_dir.name}/{day_dir.name}'",
                    )

                try:
                    content = metadata_file.read_text(encoding="utf-8").strip()
                    lines = content.split("\n")

                    if len(lines) != 2:  # noqa: PLR2004
                        msg = (
                            f"metadata_analyse.txt in '{month_dir.name}/{day_dir.name}' "
                            f"has {len(lines)} lines, expected 2"
                        )
                        return EvaluationReason(value=0.0, reason=msg)

                    # Check each line
                    for line_num, line in enumerate(lines, 1):
                        error = _validate_metadata_line(
                            line, line_num, expected_month, day, month_dir.name, day_dir.name
                        )
                        if error:
                            return error

                except (OSError, UnicodeDecodeError) as e:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Error reading metadata_analyse.txt in '{month_dir.name}/{day_dir.name}': {e}",
                    )

        return 1.0
