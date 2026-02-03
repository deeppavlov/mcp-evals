"""MirrorDirectoryExists evaluator for structure_mirror task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.structure_mirror.constants import MIRROR_DIR_NAME
from mcp_evals.contrib.filesystem.tasks.structure_mirror.task import find_mirror_directory

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.structure_mirror.task import StructureMirrorTask


@dataclass
class MirrorDirectoryExists(Evaluator["StructureMirrorTask", AgentRunResult]):
    """Evaluator that checks mirror directory exists."""

    async def evaluate(self, ctx: EvaluatorContext[StructureMirrorTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the mirror directory exists."""
        task = ctx.inputs
        mirror_dir = find_mirror_directory(task.work_dir)

        if mirror_dir is None:
            return EvaluationReason(
                value=0.0,
                reason=f"Mirror directory '{MIRROR_DIR_NAME}' not found",
            )

        return 1.0
