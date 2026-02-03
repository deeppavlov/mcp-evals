"""Debugging task for filesystem domain."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.common_evaluators import FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

CORRECT_FIXES = [
    "self.fp2 = PointnetFPModule(mlp=[256+256,256,256])",
    "self.fp2 = PointnetFPModule(mlp=[512,256,256])",
]


@dataclass
class AnswerFormat(Evaluator["DebuggingTask", AgentRunResult]):
    """Evaluator that checks answer file has correct format."""

    async def evaluate(self, ctx: EvaluatorContext["DebuggingTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the answer file has the correct format."""
        task = ctx.inputs
        answer_file = task.work_dir / "answer.txt"

        try:
            content = answer_file.read_text(encoding="utf-8").strip()

            if not content:
                return EvaluationReason(value=0.0, reason="Answer file is empty")

            if len(content.split("\n")) > 1:
                return EvaluationReason(
                    value=0.0,
                    reason="Answer file contains multiple lines or additional text",
                )

            if "models/backbone_module.py" not in content:
                return EvaluationReason(
                    value=0.0,
                    reason="Answer should contain 'models/backbone_module.py'",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error reading answer file: {e}")

        return 1.0


@dataclass
class FilePathStructure(Evaluator["DebuggingTask", AgentRunResult]):
    """Evaluator that checks file path has expected structure."""

    async def evaluate(self, ctx: EvaluatorContext["DebuggingTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the file path has the expected structure."""
        task = ctx.inputs
        answer_file = task.work_dir / "answer.txt"

        try:
            content = answer_file.read_text(encoding="utf-8").strip()

            expected_components = ["models", "backbone_module.py"]

            for component in expected_components:
                if component not in content:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Answer missing expected component: {component}",
                    )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying answer structure: {e}")

        return 1.0


@dataclass
class BugFix(Evaluator["DebuggingTask", AgentRunResult]):
    """Evaluator that checks bug has been fixed in the code."""

    async def evaluate(self, ctx: EvaluatorContext["DebuggingTask", AgentRunResult]) -> EvaluatorOutput:
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


class DebuggingTask(FilesystemTask):
    """Task for debugging VoteNet backbone module.

    The agent must:
    1. Examine the codebase to identify the bug
    2. Fix the bug in models/backbone_module.py
    3. Change self.fp2 = PointnetFPModule(mlp=[256,256,256]) to mlp=[512,256,256] or [256+256,256,256]
    4. Create answer.txt with the bug location path
    """

    name = "debugging"
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

There is a bug in the VoteNet backbone module that needs to be identified and fixed.

### Task Objectives

1. **Examine the codebase** using filesystem MCP tools
2. **Identify the bug** inside the whole process
3. **Fix the bug** in the code
4. **Create an answer file** with the bug location

### Expected Output

1. **Fix the bug** in the code file directly
2. **Create `answer.txt`** in the test directory root with the format: `path`

**Requirements:**
- Only include the bug's file path in answer.txt
- No additional text or explanation

### Hint

**The bug is not in demo.py**, please look deeper inside the codebase.

### Bug Details

The bug is in `models/backbone_module.py`:
- Line containing `self.fp2 = PointnetFPModule(mlp=[256,256,256])`
- Should be changed to `self.fp2 = PointnetFPModule(mlp=[512,256,256])` or \
`self.fp2 = PointnetFPModule(mlp=[256+256,256,256])`

### Success Criteria

- answer.txt contains the path to models/backbone_module.py
- The bug in the file has been fixed (mlp parameter corrected)"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FileExists("answer.txt"),
            AnswerFormat(),
            FilePathStructure(),
            BugFix(),
        )
