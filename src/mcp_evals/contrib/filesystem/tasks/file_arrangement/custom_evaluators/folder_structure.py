"""FolderStructure evaluator for file_arrangement task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.file_arrangement.constants import REQUIRED_FOLDERS

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.file_arrangement.task import FileArrangementTask


@dataclass
class FolderStructure(Evaluator["FileArrangementTask", AgentRunResult]):
    """Evaluator that checks all required folders exist."""

    async def evaluate(self, ctx: EvaluatorContext[FileArrangementTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that all required folders exist."""
        task = ctx.inputs

        missing_folders = []
        for folder in REQUIRED_FOLDERS:
            folder_path = task.work_dir / folder
            if not folder_path.exists() or not folder_path.is_dir():
                missing_folders.append(folder)

        if missing_folders:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing required folders: {missing_folders}",
            )

        return 1.0
