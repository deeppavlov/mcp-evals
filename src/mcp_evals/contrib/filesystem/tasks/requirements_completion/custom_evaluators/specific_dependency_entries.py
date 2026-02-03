"""SpecificDependencyEntries evaluator for requirements_completion task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.requirements_completion.task import RequirementsCompletionTask


@dataclass
class SpecificDependencyEntries(Evaluator["RequirementsCompletionTask", AgentRunResult]):
    """Evaluator that checks specific dependency entries are present."""

    async def evaluate(self, ctx: EvaluatorContext[RequirementsCompletionTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the specific dependency entries are present."""
        task = ctx.inputs
        requirements_file = task.work_dir / "requirements.txt"

        try:
            content = requirements_file.read_text(encoding="utf-8")

            required_checks = [
                ("einops", "einops"),
                ("kornia", "kornia"),
                ("taming", "taming"),
            ]

            missing_entries = []
            found_entries = []

            for check_name, _ in required_checks:
                if check_name in content.lower():
                    found_entries.append(check_name)
                else:
                    missing_entries.append(check_name)

            lines = content.split("\n")
            openai_clip_found = False
            for line in lines:
                line_lower = line.lower()
                if "openai" in line_lower and "clip" in line_lower:
                    openai_clip_found = True
                    break

            if openai_clip_found:
                found_entries.append("openai+clip")
            else:
                missing_entries.append("openai+clip")

            if missing_entries:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing required dependency checks: {missing_entries}",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking specific entries: {e}")

        return 1.0
