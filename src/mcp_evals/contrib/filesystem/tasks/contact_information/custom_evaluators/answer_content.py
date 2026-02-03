"""AnswerContent evaluator for contact_information task."""

from dataclasses import dataclass

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput


@dataclass
class AnswerContent(Evaluator["ContactInformationTask", AgentRunResult]):
    """Evaluator that checks answer.txt contains correct answer about Charlie Davis."""

    async def evaluate(self, ctx: EvaluatorContext["ContactInformationTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the answer.txt contains the correct answer about Charlie Davis."""
        task = ctx.inputs
        answer_file = task.work_dir / "answer.txt"

        try:
            content = answer_file.read_text(encoding="utf-8").strip().lower()

            if "dentist" in content:
                return 1.0

            return EvaluationReason(
                value=0.0,
                reason=f"Answer does not contain 'dentist'. Found: '{content}'",
            )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error reading answer.txt: {e}")

