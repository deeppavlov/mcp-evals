"""Find Math Paper task for filesystem domain."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.common_evaluators import FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture


@dataclass
class AnswerFileExists(Evaluator["FindMathPaperTask", AgentRunResult]):
    """Evaluator that checks answer.html exists in the papers directory."""

    async def evaluate(self, ctx: EvaluatorContext["FindMathPaperTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that answer.html exists in the papers directory."""
        task = ctx.inputs
        answer_file = task.work_dir / "answer.html"

        if not answer_file.exists():
            return EvaluationReason(value=0.0, reason="File 'answer.html' not found")

        return 1.0


@dataclass
class OriginalFileRemoved(Evaluator["FindMathPaperTask", AgentRunResult]):
    """Evaluator that checks the original file (2407.01284.html) no longer exists."""

    async def evaluate(self, ctx: EvaluatorContext["FindMathPaperTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the original file (2407.01284.html) no longer exists."""
        task = ctx.inputs
        original_file = task.work_dir / "2407.01284.html"

        if original_file.exists():
            return EvaluationReason(
                value=0.0,
                reason="Original file 2407.01284.html still exists",
            )

        return 1.0


class FindMathPaperTask(FilesystemTask):
    """Task for finding a math-related benchmark paper and renaming it.

    The agent must:
    1. Find a math-related benchmark paper that checks answer correctness
    2. Analyze whether model suffers from insufficient knowledge, lacks generalization, or relies on rote memorization
    3. Rename the corresponding HTML file to answer.html
    """

    name = "find_math_paper"
    goal = """Please use FileSystem tools to finish the following task:

You are given a directory containing multiple paper files. Please help me find a math-related benchmark paper. I don't remember its name, but I remember it not only checks whether the answer is correct, but also analyzes whether the model suffers from insufficient knowledge, lacks generalization ability, or relies on rote memorization. After finding this paper, rename its corresponding HTML file to `answer.html`."""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            AnswerFileExists(),
            OriginalFileRemoved(),
        )

