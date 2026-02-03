"""NoFilesCopied evaluator for structure_mirror task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.structure_mirror.constants import MIRROR_DIR_NAME, SOURCE_DIR_NAME
from mcp_evals.contrib.filesystem.tasks.structure_mirror.task import find_mirror_directory

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.structure_mirror.task import StructureMirrorTask


@dataclass
class NoFilesCopied(Evaluator["StructureMirrorTask", AgentRunResult]):
    """Evaluator that checks no file contents were copied, only directory structure."""

    async def evaluate(self, ctx: EvaluatorContext[StructureMirrorTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that no file contents were copied, only directory structure."""
        task = ctx.inputs
        source_dir = task.work_dir / SOURCE_DIR_NAME
        mirror_dir = find_mirror_directory(task.work_dir)

        if mirror_dir is None:
            return EvaluationReason(value=0.0, reason=f"Mirror directory '{MIRROR_DIR_NAME}' not found")

        if not source_dir.exists():
            return EvaluationReason(value=0.0, reason=f"Source directory '{SOURCE_DIR_NAME}' not found")

        try:
            # Check that no files from source were copied (except placeholder.txt files)
            for source_file in source_dir.rglob("*"):
                if source_file.is_file():
                    relative_path = source_file.relative_to(source_dir)
                    mirror_file = mirror_dir / relative_path

                    # Skip if this would be a placeholder.txt file
                    if mirror_file.name == "placeholder.txt":
                        continue

                    if mirror_file.exists():
                        return EvaluationReason(
                            value=0.0,
                            reason=f"File was copied when it shouldn't be: {relative_path}",
                        )
        except (OSError, PermissionError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking copied files: {e}")

        return 1.0
