"""Code Locating task for filesystem domain."""

import re
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.common_evaluators import FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture


@dataclass
class AnswerFileExists(Evaluator["CodeLocatingTask", AgentRunResult]):
    """Evaluator that checks answer.txt file exists."""

    async def evaluate(self, ctx: EvaluatorContext["CodeLocatingTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the answer.txt file exists."""
        task = ctx.inputs
        answer_file = task.work_dir / "answer.txt"

        if not answer_file.exists():
            return EvaluationReason(value=0.0, reason="File 'answer.txt' not found")

        return 1.0


@dataclass
class AnswerFormat(Evaluator["CodeLocatingTask", AgentRunResult]):
    """Evaluator that checks answer file has correct format."""

    async def evaluate(self, ctx: EvaluatorContext["CodeLocatingTask", AgentRunResult]) -> EvaluatorOutput:
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

            if "\\" in content:
                return EvaluationReason(
                    value=0.0,
                    reason="Answer uses backslashes instead of forward slashes",
                )

            if content.startswith("/") or ":" in content:
                return EvaluationReason(
                    value=0.0,
                    reason="Answer appears to be an absolute path",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error reading answer file: {e}")

        return 1.0


@dataclass
class FilePathStructure(Evaluator["CodeLocatingTask", AgentRunResult]):
    """Evaluator that checks file path has expected structure."""

    async def evaluate(self, ctx: EvaluatorContext["CodeLocatingTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the file path has the expected structure."""
        task = ctx.inputs
        answer_file = task.work_dir / "answer.txt"

        try:
            content = answer_file.read_text(encoding="utf-8").strip()

            expected_components = ["threestudio", "models", "guidance", "zero123_guidance.py"]

            for component in expected_components:
                if component not in content:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Path missing expected component: {component}",
                    )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying file: {e}")

        return 1.0


@dataclass
class FileExists(Evaluator["CodeLocatingTask", AgentRunResult]):
    """Evaluator that checks identified file actually exists."""

    async def evaluate(self, ctx: EvaluatorContext["CodeLocatingTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the identified file actually exists."""
        task = ctx.inputs
        answer_file = task.work_dir / "answer.txt"

        try:
            content = answer_file.read_text(encoding="utf-8").strip()

            file_path = task.work_dir / content

            if not file_path.exists():
                if content.startswith("threestudio/models/"):
                    corrected_path = content.replace(
                        "threestudio/models/",
                        "threestudio/threestudio/models/",
                    )
                    file_path = task.work_dir / corrected_path
                    if file_path.exists():
                        return 1.0

                return EvaluationReason(
                    value=0.0,
                    reason=f"Identified file does not exist: {content}",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying file: {e}")

        return 1.0


@dataclass
class Zero123GuidanceContent(Evaluator["CodeLocatingTask", AgentRunResult]):
    """Evaluator that checks identified file contains Zero123 guidance implementation."""

    async def evaluate(self, ctx: EvaluatorContext["CodeLocatingTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the identified file actually contains Zero123 guidance implementation."""
        task = ctx.inputs
        answer_file = task.work_dir / "answer.txt"

        try:
            content = answer_file.read_text(encoding="utf-8").strip()

            file_path = task.work_dir / content

            if not file_path.exists():
                if content.startswith("threestudio/models/"):
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
                "class Zero123Guidance" in file_content
                and '@threestudio.register("zero123-guidance")' in file_content
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


class CodeLocatingTask(FilesystemTask):
    """Task for finding Zero123 guidance implementation file.

    The agent must:
    1. Explore the ThreeStudio codebase
    2. Identify the file that contains Zero123 guidance implementation
    3. Create answer.txt with the correct file path
    4. The file should contain class Zero123Guidance and @threestudio.register("zero123-guidance")
    """

    name = "code_locating"
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

ThreeStudio is a comprehensive codebase that implements various diffusion-based text-to-3D models, including NeRF-based rendering stage and diffusion guidance stage. Your task is to explore the codebase and identify the specific file that defines the guidance functionality for the Zero123 model.

### Task Objectives

1. **Explore the ThreeStudio codebase** using filesystem MCP tools
2. **Search through the project structure** to understand the codebase organization
3. **Identify the file** that contains the Zero123 guidance implementation
4. **Create an answer file** with the correct file path

### Expected Output

Create a file named `answer.txt` in the test directory root

**Requirements:**
- Only include the file path, no additional text or explanation
- Use forward slashes (/) for path separators
- Include the full relative path from the project root
- Ensure the path points to the actual file that defines Zero123 guidance

### Success Criteria

The answer file should contain the path to `zero123_guidance.py` which:
- Contains the class `Zero123Guidance`
- Has the decorator `@threestudio.register("zero123-guidance")`
- Is located in the models/guidance directory"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            AnswerFileExists(),
            AnswerFormat(),
            FilePathStructure(),
            FileExists(),
            Zero123GuidanceContent(),
        )

