"""File Merging task for filesystem domain."""

from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.common_evaluators import FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

# Expected files (10 smallest files, excluding file_12.txt) in alphabetical order
EXPECTED_FILES = [
    "file_10.txt",
    "file_11.txt",
    "file_13.txt",
    "file_14.txt",
    "file_15.txt",
    "file_16.txt",
    "file_17.txt",
    "file_18.txt",
    "file_19.txt",
    "file_20.txt",
]


class CorrectFilesSelected(Evaluator["FileMergingTask", AgentRunResult]):
    """Evaluator that checks correct 10 files were selected and included."""

    async def evaluate(self, ctx: EvaluatorContext["FileMergingTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the correct 10 files were selected and included."""
        task = ctx.inputs
        merged_file = task.work_dir / "merged_content.txt"

        if not merged_file.exists():
            return EvaluationReason(value=0.0, reason="File 'merged_content.txt' not found")

        try:
            content = merged_file.read_text(encoding="utf-8")

            # Check if all expected files are present
            for expected_file in EXPECTED_FILES:
                if expected_file not in content:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Expected file '{expected_file}' not found in merged content",
                    )

            # Check if file_12.txt is NOT present (should be excluded)
            if "file_12.txt" in content:
                return EvaluationReason(
                    value=0.0,
                    reason="file_12.txt should be excluded but was found in merged content",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying file selection: {e}")

        return 1.0


class AlphabeticalOrder(Evaluator["FileMergingTask", AgentRunResult]):
    """Evaluator that checks files are in alphabetical order."""

    async def evaluate(self, ctx: EvaluatorContext["FileMergingTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that files are in alphabetical order."""
        task = ctx.inputs
        merged_file = task.work_dir / "merged_content.txt"

        if not merged_file.exists():
            return EvaluationReason(value=0.0, reason="File 'merged_content.txt' not found")

        try:
            content = merged_file.read_text(encoding="utf-8")
            lines = content.split("\n")

            # Extract filenames from the content (lines that contain .txt)
            found_files = []
            for line in lines:
                line_ = line.strip()
                # Check if this line contains any of the expected filenames
                for expected_file in EXPECTED_FILES:
                    if expected_file in line_:
                        found_files.append(expected_file)
                        break

            # Check if files are in alphabetical order
            if found_files != EXPECTED_FILES:
                msg = f"Files not in correct alphabetical order. Expected: {EXPECTED_FILES}, Found: {found_files}"
                return EvaluationReason(value=0.0, reason=msg)

        except (ValueError, OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying alphabetical order: {e}")

        return 1.0


class FilenameHeaders(Evaluator["FileMergingTask", AgentRunResult]):
    """Evaluator that checks each file section starts with correct filename header."""

    async def evaluate(self, ctx: EvaluatorContext["FileMergingTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that each file section starts with the correct filename header."""
        task = ctx.inputs
        merged_file = task.work_dir / "merged_content.txt"

        if not merged_file.exists():
            return EvaluationReason(value=0.0, reason="File 'merged_content.txt' not found")

        try:
            content = merged_file.read_text(encoding="utf-8")

            for expected_file in EXPECTED_FILES:
                # Check if the filename appears anywhere in the content (as part of a line)
                if expected_file not in content:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Filename header '{expected_file}' not found",
                    )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying filename headers: {e}")

        return 1.0


class FileContentIntegrity(Evaluator["FileMergingTask", AgentRunResult]):
    """Evaluator that checks content of each file is preserved correctly."""

    async def evaluate(self, ctx: EvaluatorContext["FileMergingTask", AgentRunResult]) -> EvaluatorOutput:  # noqa: C901
        """Verify that the content of each file is preserved correctly."""
        task = ctx.inputs
        merged_file = task.work_dir / "merged_content.txt"

        if not merged_file.exists():
            return EvaluationReason(value=0.0, reason="File 'merged_content.txt' not found")

        try:
            content = merged_file.read_text(encoding="utf-8")
            lines = content.split("\n")

            for expected_file in EXPECTED_FILES:
                # Get the original file content
                original_file = task.work_dir / expected_file
                if not original_file.exists():
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Original file '{expected_file}' not found",
                    )

                original_content = original_file.read_text(encoding="utf-8").strip()

                # Find the line index where this file's header appears
                header_line_index = -1
                for i, line in enumerate(lines):
                    if expected_file in line:
                        header_line_index = i
                        break

                if header_line_index == -1:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Could not find header for {expected_file}",
                    )

                # Find the next header line or end of file
                next_header_index = len(lines)
                for i in range(header_line_index + 1, len(lines)):
                    for other_file in EXPECTED_FILES:
                        if other_file != expected_file and other_file in lines[i]:
                            next_header_index = i
                            break
                    if next_header_index != len(lines):
                        break

                # Extract content lines (from header + 1 to next header)
                content_lines = lines[header_line_index + 1 : next_header_index]
                merged_content = "\n".join(content_lines).strip()

                if merged_content != original_content:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Content mismatch for {expected_file}",
                    )

        except (ValueError, OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying content integrity: {e}")

        return 1.0


class FileMergingTask(FilesystemTask):
    """Task for merging smallest files in alphabetical order.

    The agent must:
    1. Identify the 10 smallest .txt files (excluding file_12.txt)
    2. Sort the selected files alphabetically by filename
    3. Merge the content into merged_content.txt
    4. Add file headers before each file's content
    5. Maintain the original content without modifications
    """

    name = "file_merging"
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

You are given a directory containing multiple text files of varying sizes. Your task is to identify the 10 smallest \
.txt files, merge their content in alphabetical order, and create a consolidated file called "merged_content.txt" \
with proper formatting.

### Task Objectives

1. **Identify the 10 smallest .txt files** in the test directory (excluding file_12.txt)
2. **Sort the selected files alphabetically** by filename
3. **Merge the content** of these files into a single file named `merged_content.txt`
4. **Add file headers** (file name) before each file's content
5. **Maintain the original content** of each file without modifications

### Expected Output

- File name: `merged_content.txt`
- Content should include all 10 files in alphabetical order
- Each file section should start with the filename
- Original file content should be preserved exactly"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FileExists("merged_content.txt"),
            CorrectFilesSelected(),
            AlphabeticalOrder(),
            FilenameHeaders(),
            FileContentIntegrity(),
        )
