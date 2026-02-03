"""RequiredDependenciesPresent evaluator for requirements_completion task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.requirements_completion.constants import REQUIRED_DEPS

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.requirements_completion.task import RequirementsCompletionTask


@dataclass
class RequiredDependenciesPresent(Evaluator["RequirementsCompletionTask", AgentRunResult]):
    """Evaluator that checks all required Zero123 dependencies are present."""

    async def evaluate(self, ctx: EvaluatorContext[RequirementsCompletionTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that all required Zero123 dependencies are present."""
        task = ctx.inputs
        requirements_file = task.work_dir / "requirements.txt"

        try:
            content = requirements_file.read_text(encoding="utf-8")

            missing_deps = []
            found_deps = []

            for dep in REQUIRED_DEPS:
                if dep.lower() in content.lower():
                    found_deps.append(dep)
                else:
                    missing_deps.append(dep)

            if missing_deps:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing required dependencies: {missing_deps}",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking dependencies: {e}")

        return 1.0
