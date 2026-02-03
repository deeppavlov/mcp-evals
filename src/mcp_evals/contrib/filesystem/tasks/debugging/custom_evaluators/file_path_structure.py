"""FilePathStructure evaluator for debugging task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.debugging.task import DebuggingTask


@dataclass
class FilePathStructure(Evaluator["DebuggingTask", AgentRunResult]):
    """Evaluator that checks file path has expected structure."""

    async def evaluate(self, ctx: EvaluatorContext[DebuggingTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the file path has the expected structure."""
        task = ctx.inputs
        answer_file = task.work_dir / "answer.txt"

        try:
            content = answer_file.read_text(encoding="utf-8").strip()

            expected_components = ["models", "backbone_module.py"]

            for component in expected_components:
                if component not in content:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Answer missing expected component: {component}",
                    )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying answer structure: {e}")

        return 1.0
