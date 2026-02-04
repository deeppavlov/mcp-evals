"""UppercaseContent evaluator for uppercase task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.uppercase.constants import EXPECTED_FILES

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.uppercase.task import UppercaseTask


@dataclass
class UppercaseContent(Evaluator["UppercaseTask", AgentRunResult]):
    """Evaluator that checks uppercase files contain correct uppercase content."""

    async def evaluate(self, ctx: EvaluatorContext[UppercaseTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that uppercase files contain the correct uppercase content."""
        task = ctx.inputs
        uppercase_dir = task.work_dir / "uppercase"

        for filename in EXPECTED_FILES:
            original_file = task.work_dir / filename
            uppercase_file = uppercase_dir / filename

            if not original_file.exists():
                return EvaluationReason(
                    value=0.0,
                    reason=f"Original file '{filename}' not found",
                )

            try:
                original_content = original_file.read_text(encoding="utf-8")
                uppercase_content = uppercase_file.read_text(encoding="utf-8")

                # Check if uppercase content is the uppercase version of original
                expected_uppercase = original_content.upper()

                if uppercase_content != expected_uppercase:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"File '{filename}' content is not properly converted to uppercase",
                    )

            except (OSError, UnicodeDecodeError) as e:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Error reading file '{filename}': {e}",
                )

        return 1.0
