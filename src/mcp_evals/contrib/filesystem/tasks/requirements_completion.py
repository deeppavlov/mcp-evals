"""Requirements Completion task for filesystem domain."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.common_evaluators import FileExists, FileReadable
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

REQUIRED_DEPS = ["einops", "kornia", "taming", "openai", "clip"]


@dataclass
class RequiredDependenciesPresent(Evaluator["RequirementsCompletionTask", AgentRunResult]):
    """Evaluator that checks all required Zero123 dependencies are present."""

    async def evaluate(self, ctx: EvaluatorContext["RequirementsCompletionTask", AgentRunResult]) -> EvaluatorOutput:
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


@dataclass
class SpecificDependencyEntries(Evaluator["RequirementsCompletionTask", AgentRunResult]):
    """Evaluator that checks specific dependency entries are present."""

    async def evaluate(self, ctx: EvaluatorContext["RequirementsCompletionTask", AgentRunResult]) -> EvaluatorOutput:
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


@dataclass
class FileFormat(Evaluator["RequirementsCompletionTask", AgentRunResult]):
    """Evaluator that checks requirements.txt file has proper format."""

    async def evaluate(self, ctx: EvaluatorContext["RequirementsCompletionTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the requirements.txt file has proper format."""
        task = ctx.inputs
        requirements_file = task.work_dir / "requirements.txt"

        try:
            content = requirements_file.read_text(encoding="utf-8")

            if not content.strip():
                return EvaluationReason(value=0.0, reason="File is completely empty")

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking file: {e}")

        return 1.0


@dataclass
class NoDuplicateEntries(Evaluator["RequirementsCompletionTask", AgentRunResult]):
    """Evaluator that checks there are no duplicate dependency entries."""

    async def evaluate(self, ctx: EvaluatorContext["RequirementsCompletionTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that there are no duplicate dependency entries."""
        task = ctx.inputs
        requirements_file = task.work_dir / "requirements.txt"

        try:
            content = requirements_file.read_text(encoding="utf-8")

            if len(content) < 10:  # noqa: PLR2004
                return EvaluationReason(value=0.0, reason="File seems too short to be valid")

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking file: {e}")

        return 1.0


class RequirementsCompletionTask(FilesystemTask):
    """Task for restoring Zero123 dependencies in requirements.txt.

    The agent must:
    1. Locate the requirements.txt file
    2. Identify missing Zero123 dependencies
    3. Add required dependencies: einops, kornia, taming, openai, clip
    4. Ensure openai and clip are on the same line
    5. Ensure file format is correct
    """

    name = "requirements_completion"
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

The `requirements.txt` file in the ThreeStudio project is used to install necessary Python libraries. \
However, the Zero123-related dependencies were accidentally deleted from the file. Your task is to \
restore these missing dependencies.

### Task Objectives

1. **Locate the requirements.txt file** in the test environment
2. **Identify the missing Zero123 dependencies** that need to be restored
3. **Add the required dependencies** to the requirements.txt file
4. **Ensure the file format is correct** (one dependency per line)

### Required Dependencies to Restore

The following dependencies must be present in requirements.txt:
- einops
- kornia
- taming (taming-transformers-rom1504)
- openai and clip should be on the same line (openai-clip)

### Expected Output

The `requirements.txt` file should:
- Contain all five required dependencies (einops, kornia, taming, openai, clip)
- Have openai and clip on the same line
- Be properly formatted
- Be non-empty and valid

### Success Criteria

- requirements.txt file exists and is readable
- All required dependencies are present
- File format is valid"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FileExists("requirements.txt"),
            FileReadable("requirements.txt"),
            RequiredDependenciesPresent(),
            SpecificDependencyEntries(),
            FileFormat(),
            NoDuplicateEntries(),
        )
