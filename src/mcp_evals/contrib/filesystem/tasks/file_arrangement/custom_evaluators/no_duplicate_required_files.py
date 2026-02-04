"""NoDuplicateRequiredFiles evaluator for file_arrangement task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.file_arrangement.constants import ALL_REQUIRED_FILES, REQUIRED_FOLDERS

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.file_arrangement.task import FileArrangementTask


@dataclass
class NoDuplicateRequiredFiles(Evaluator["FileArrangementTask", AgentRunResult]):
    """Evaluator that checks the 18 required files are not duplicated across folders."""

    async def evaluate(self, ctx: EvaluatorContext[FileArrangementTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the 18 required files are not duplicated across folders."""
        task = ctx.inputs

        file_locations: dict[str, str] = {}
        duplicates = []

        for folder in REQUIRED_FOLDERS:
            folder_path = task.work_dir / folder
            if folder_path.exists() and folder_path.is_dir():
                try:
                    for file_path in folder_path.iterdir():
                        if file_path.is_file() and file_path.name in ALL_REQUIRED_FILES:
                            if file_path.name in file_locations:
                                duplicates.append(
                                    f"{file_path.name} (in {file_locations[file_path.name]} and {folder}/)",
                                )
                            else:
                                file_locations[file_path.name] = f"{folder}/"
                except (OSError, PermissionError):
                    continue

        if duplicates:
            return EvaluationReason(
                value=0.0,
                reason=f"Duplicate required files found: {duplicates}",
            )

        return 1.0
