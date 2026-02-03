"""FileSizes evaluator for size_classification task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.size_classification.constants import (
    MEDIUM_FILE_MAX,
    MEDIUM_FILE_MIN,
    SIZE_RANGES,
    SYSTEM_FILES,
)

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.size_classification.task import SizeClassificationTask


@dataclass
class FileSizes(Evaluator["SizeClassificationTask", AgentRunResult]):
    """Evaluator that checks files are actually in the correct size categories."""

    async def evaluate(self, ctx: EvaluatorContext[SizeClassificationTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that files are actually in the correct size categories."""
        task = ctx.inputs

        for dir_name in SIZE_RANGES:
            dir_path = task.work_dir / dir_name

            try:
                for file_path in dir_path.iterdir():
                    if file_path.is_file() and file_path.name not in SYSTEM_FILES:
                        file_size = file_path.stat().st_size

                        if dir_name == "small_files" and file_size >= MEDIUM_FILE_MIN:
                            msg = f"File {file_path.name} in small_files but size is {file_size} bytes"
                            return EvaluationReason(value=0.0, reason=msg)

                        if dir_name == "medium_files" and (file_size < MEDIUM_FILE_MIN or file_size > MEDIUM_FILE_MAX):
                            msg = f"File {file_path.name} in medium_files but size is {file_size} bytes"
                            return EvaluationReason(value=0.0, reason=msg)

                        if dir_name == "large_files" and file_size <= MEDIUM_FILE_MAX:
                            msg = f"File {file_path.name} in large_files but size is {file_size} bytes"
                            return EvaluationReason(value=0.0, reason=msg)
            except (OSError, PermissionError) as e:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Error checking file sizes in '{dir_name}': {e}",
                )

        return 1.0
