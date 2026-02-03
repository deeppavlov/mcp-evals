"""ArchivesFolderFiles evaluator for file_arrangement task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.file_arrangement.constants import REQUIRED_FILE_MAPPING

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.file_arrangement.task import FileArrangementTask


@dataclass
class ArchivesFolderFiles(Evaluator["FileArrangementTask", AgentRunResult]):
    """Evaluator that checks archives folder contains required files."""

    async def evaluate(self, ctx: EvaluatorContext[FileArrangementTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that archives folder contains the required files."""
        task = ctx.inputs
        archives_dir = task.work_dir / "archives"

        missing_files = []
        for file_name in REQUIRED_FILE_MAPPING["archives"]:
            file_path = archives_dir / file_name
            if not file_path.exists():
                missing_files.append(file_name)

        if missing_files:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing required files in archives/ folder: {missing_files}",
            )

        return 1.0
