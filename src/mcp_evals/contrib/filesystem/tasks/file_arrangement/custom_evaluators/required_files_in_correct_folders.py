"""RequiredFilesInCorrectFolders evaluator for file_arrangement task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.file_arrangement.constants import REQUIRED_FILE_MAPPING

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.file_arrangement.task import FileArrangementTask


@dataclass
class RequiredFilesInCorrectFolders(Evaluator["FileArrangementTask", AgentRunResult]):
    """Evaluator that checks all 18 required files are in their correct designated folders."""

    async def evaluate(self, ctx: EvaluatorContext[FileArrangementTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that all 18 required files are in their correct designated folders."""
        task = ctx.inputs

        missing_files = []
        for folder, files in REQUIRED_FILE_MAPPING.items():
            folder_path = task.work_dir / folder
            for file_name in files:
                file_path = folder_path / file_name
                if not file_path.exists():
                    missing_files.append(f"{folder}/{file_name}")

        if missing_files:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing required files: {missing_files}",
            )

        return 1.0
