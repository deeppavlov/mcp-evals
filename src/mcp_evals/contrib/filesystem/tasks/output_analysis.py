"""Output Analysis task for filesystem domain."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.common_evaluators import FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

REQUIRED_STRINGS = ["loss_sds", "grad_norm", "min_step", "max_step"]
EXPECTED_FILE_PATH = "threestudio/models/guidance/zero123_guidance.py"


@dataclass
class AnswerFileExists(Evaluator["OutputAnalysisTask", AgentRunResult]):
    """Evaluator that checks answer.txt file exists."""

    async def evaluate(self, ctx: EvaluatorContext["OutputAnalysisTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the answer.txt file exists."""
        task = ctx.inputs
        answer_file = task.work_dir / "answer.txt"

        if not answer_file.exists():
            return EvaluationReason(value=0.0, reason="File 'answer.txt' not found")

        return 1.0


@dataclass
class RequiredStrings(Evaluator["OutputAnalysisTask", AgentRunResult]):
    """Evaluator that checks answer contains the four required strings."""

    async def evaluate(self, ctx: EvaluatorContext["OutputAnalysisTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the answer contains the four required strings."""
        task = ctx.inputs
        answer_file = task.work_dir / "answer.txt"

        try:
            content = answer_file.read_text(encoding="utf-8")

            missing_strings = []
            for string in REQUIRED_STRINGS:
                if string not in content:
                    missing_strings.append(string)

            if missing_strings:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing required strings: {missing_strings}",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error reading answer file: {e}")

        return 1.0


@dataclass
class LineNumbers(Evaluator["OutputAnalysisTask", AgentRunResult]):
    """Evaluator that checks line numbers contain (323 or 324) AND (327 or 328)."""

    async def evaluate(self, ctx: EvaluatorContext["OutputAnalysisTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that line numbers contain (323 or 324) AND (327 or 328)."""
        task = ctx.inputs
        answer_file = task.work_dir / "answer.txt"

        try:
            content = answer_file.read_text(encoding="utf-8")

            has_first = "323" in content or "324" in content
            has_second = "327" in content or "328" in content

            if not has_first:
                return EvaluationReason(
                    value=0.0,
                    reason="Missing first line number (323 or 324)",
                )

            if not has_second:
                return EvaluationReason(
                    value=0.0,
                    reason="Missing second line number (327 or 328)",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying line numbers: {e}")

        return 1.0


@dataclass
class FilePath(Evaluator["OutputAnalysisTask", AgentRunResult]):
    """Evaluator that checks file path contains the exact expected path string."""

    async def evaluate(self, ctx: EvaluatorContext["OutputAnalysisTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the file path contains the exact expected path string."""
        task = ctx.inputs
        answer_file = task.work_dir / "answer.txt"

        try:
            content = answer_file.read_text(encoding="utf-8")

            if EXPECTED_FILE_PATH not in content:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing expected file path: {EXPECTED_FILE_PATH}",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying file: {e}")

        return 1.0


class OutputAnalysisTask(FilesystemTask):
    """Task for analyzing Zero123 guidance output structure.

    The agent must:
    1. Find the output of guidance_out at line 137 in threestudio/systems/zero123.py
    2. State the structure and where it's found (file and line numbers)
    3. Create answer.txt with four required fields: loss_sds, grad_norm, min_step, max_step
    4. Include line numbers (323-324 and 327-328) and file path
    """

    name = "output_analysis"
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

ThreeStudio is a comprehensive codebase that implements various diffusion-based text-to-3D models, including NeRF-based rendering stage and diffusion guidance stage. Your task is to explore the codebase and identify the specific file that defines the guidance functionality for the Zero123 model.

### Task

What is the output of `guidance_out`, returned by the code at line 137 in `threestudio/systems/zero123.py`?

Clearly state the structure of it and where you find the answer (file and line numbers). Write your answer in a file named `answer.txt` in the test directory root. Do not add extra explanation or formatting beyond what is required by the task.

### Expected Output

Create a file named `answer.txt` containing:
- The four required output fields: loss_sds, grad_norm, min_step, max_step
- Line numbers where these fields are defined (lines 323-324 and 327-328)
- The file path: threestudio/models/guidance/zero123_guidance.py

### Success Criteria

The answer file should contain:
- All four strings: "loss_sds", "grad_norm", "min_step", "max_step"
- Line number 323 or 324
- Line number 327 or 328
- The file path "threestudio/models/guidance/zero123_guidance.py\""""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            AnswerFileExists(),
            RequiredStrings(),
            LineNumbers(),
            FilePath(),
        )

