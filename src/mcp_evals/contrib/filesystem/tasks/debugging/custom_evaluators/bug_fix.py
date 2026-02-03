"""BugFix evaluator for debugging task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.debugging.constants import CORRECT_FIXES

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.debugging.task import DebuggingTask


@dataclass
class BugFix(Evaluator["DebuggingTask", AgentRunResult]):
    """Evaluator that checks bug has been fixed in the code."""

    async def evaluate(self, ctx: EvaluatorContext[DebuggingTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the bug has been fixed in the code."""
        task = ctx.inputs
        file_path = task.work_dir / "models/backbone_module.py"

        try:
            if not file_path.exists():
                return EvaluationReason(
                    value=0.0,
                    reason="Cannot find file for bug fix verification: models/backbone_module.py",
                )

            file_content = file_path.read_text(encoding="utf-8")
            lines = file_content.split("\n")

            target_line = None
            target_line_number = None

            for i, line in enumerate(lines):
                if "self.fp2 = PointnetFPModule" in line:
                    target_line = line.strip()
                    target_line_number = i + 1
                    break

            if target_line is None:
                return EvaluationReason(
                    value=0.0,
                    reason="Could not find line containing 'self.fp2 = PointnetFPModule'",
                )

            original_bug = "self.fp2 = PointnetFPModule(mlp=[256,256,256])"
            if original_bug in target_line:
                return EvaluationReason(
                    value=0.0,
                    reason=(
                        f"Bug has not been fixed - original line still exists. "
                        f"Line {target_line_number} content: {target_line}"
                    ),
                )

            fix_found = False
            for fix in CORRECT_FIXES:
                if fix in target_line:
                    fix_found = True
                    break

            if not fix_found:
                return EvaluationReason(
                    value=0.0,
                    reason=(
                        f"Bug fix not found at line {target_line_number}. "
                        f"Line content: {target_line}. "
                        f"Expected one of: {CORRECT_FIXES}"
                    ),
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying bug fix: {e}")

        return 1.0
