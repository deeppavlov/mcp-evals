"""Evaluator that checks all files mentioned in answer.txt actually exist."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.pattern_matching.task import PatternMatchingTask


@dataclass
class FilesExist(Evaluator["PatternMatchingTask", AgentRunResult]):
    """Evaluator that checks all files mentioned in answer.txt actually exist."""

    async def evaluate(self, ctx: EvaluatorContext[PatternMatchingTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that all files mentioned in answer.txt actually exist."""
        task = ctx.inputs
        answer_file = task.work_dir / "answer.txt"

        if not answer_file.exists():
            return EvaluationReason(value=0.0, reason="File 'answer.txt' not found")

        try:
            content = answer_file.read_text(encoding="utf-8").strip()

            if not content:
                return 1.0  # No files to verify

            lines = content.split("\n")
            for line in lines:
                line_ = line.strip()
                if not line_:
                    continue

                filename = line_.split(",")[0]
                file_path = task.work_dir / filename

                if not file_path.exists():
                    return EvaluationReason(
                        value=0.0,
                        reason=f"File mentioned in answer does not exist: {filename}",
                    )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying file existence: {e}")

        return 1.0
