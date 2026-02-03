"""FileStatistics evaluator for structure_analysis task."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.structure_analysis.constants import (
    EXPECTED_FILE_COUNT,
    EXPECTED_FOLDER_COUNT,
    EXPECTED_SIZE,
    SIZE_TOLERANCE,
)

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.structure_analysis.task import StructureAnalysisTask


@dataclass
class FileStatistics(Evaluator["StructureAnalysisTask", AgentRunResult]):
    """Evaluator that checks file statistics are correct."""

    async def evaluate(self, ctx: EvaluatorContext[StructureAnalysisTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify subtask 1: File Statistics."""
        task = ctx.inputs
        analysis_file = task.work_dir / "structure_analysis.txt"

        try:
            content = analysis_file.read_text(encoding="utf-8")

            file_count_match = re.search(r"total number of files:\s*(\d+)", content, re.IGNORECASE)
            folder_count_match = re.search(r"total number of folders:\s*(\d+)", content, re.IGNORECASE)
            size_match = re.search(r"total size of all files:\s*(\d+)", content, re.IGNORECASE)

            if not file_count_match or not folder_count_match or not size_match:
                return EvaluationReason(
                    value=0.0,
                    reason="Could not extract file statistics from structure_analysis.txt",
                )

            file_count = int(file_count_match.group(1))
            folder_count = int(folder_count_match.group(1))
            total_size = int(size_match.group(1))

            if file_count != EXPECTED_FILE_COUNT:
                return EvaluationReason(
                    value=0.0,
                    reason=f"File count must be {EXPECTED_FILE_COUNT}, found: {file_count}",
                )

            if folder_count != EXPECTED_FOLDER_COUNT:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Folder count must be {EXPECTED_FOLDER_COUNT}, found: {folder_count}",
                )

            if abs(total_size - EXPECTED_SIZE) > SIZE_TOLERANCE:
                msg = f"Total size ({total_size}) is not within acceptable range ({EXPECTED_SIZE} ± {SIZE_TOLERANCE})"
                return EvaluationReason(value=0.0, reason=msg)

        except (OSError, UnicodeDecodeError, ValueError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying file statistics: {e}")

        return 1.0
