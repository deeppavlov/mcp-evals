"""Zero123GuidanceContent evaluator for code_locating task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.code_locating.task import CodeLocatingTask


@dataclass
class Zero123GuidanceContent(Evaluator["CodeLocatingTask", AgentRunResult]):
    """Evaluator that checks identified file contains Zero123 guidance implementation."""

    async def evaluate(self, ctx: EvaluatorContext[CodeLocatingTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the identified file actually contains Zero123 guidance implementation."""
        task = ctx.inputs
        answer_file = task.work_dir / "answer.txt"

        try:
            content = answer_file.read_text(encoding="utf-8").strip()

            file_path = task.work_dir / content

            if not file_path.exists() and content.startswith("threestudio/models/"):
                corrected_path = content.replace(
                    "threestudio/models/",
                    "threestudio/threestudio/models/",
                )
                file_path = task.work_dir / corrected_path

            if not file_path.exists():
                return EvaluationReason(
                    value=0.0,
                    reason=f"Cannot find file for content verification: {content}",
                )

            file_content = file_path.read_text(encoding="utf-8")

            is_main_implementation = (
                "class Zero123Guidance" in file_content and '@threestudio.register("zero123-guidance")' in file_content
            )

            if not is_main_implementation:
                return EvaluationReason(
                    value=0.0,
                    reason=(
                        "File is not the main Zero123 guidance implementation. "
                        "Expected: class Zero123Guidance and "
                        "@threestudio.register('zero123-guidance')"
                    ),
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying file: {e}")

        return 1.0
