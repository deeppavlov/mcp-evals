"""AllFilesAreIncluded evaluator for uppercase task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.uppercase.constants import EXPECTED_FILES

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.uppercase.task import UppercaseTask


@dataclass
class AllFilesAreIncluded(Evaluator["UppercaseTask", AgentRunResult]):
    """Evaluator that checks all 10 files are included in the answer."""

    async def evaluate(self, ctx: EvaluatorContext[UppercaseTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that all 10 files are included in the answer."""
        task = ctx.inputs
        uppercase_dir = task.work_dir / "uppercase"
        answer_file = uppercase_dir / "answer.txt"

        if not answer_file.exists():
            return EvaluationReason(value=0.0, reason="File 'answer.txt' not found")

        try:
            content = answer_file.read_text(encoding="utf-8").strip()
            lines = content.split("\n")

            # Check that all 10 files are present
            found_files = set()
            for line in lines:
                parts = line.split(":", 1)
                filename = parts[0]
                found_files.add(filename)

            expected_files = set(EXPECTED_FILES)

            if found_files != expected_files:
                missing = expected_files - found_files
                extra = found_files - expected_files
                msg_parts = []
                if missing:
                    msg_parts.append(f"Missing files: {sorted(missing)}")
                if extra:
                    msg_parts.append(f"Extra files: {sorted(extra)}")
                return EvaluationReason(value=0.0, reason=", ".join(msg_parts))

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying file inclusion: {e}")

        return 1.0
