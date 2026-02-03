"""File Splitting task for filesystem domain."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.common_evaluators import DirectoryExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

# Expected split files
EXPECTED_SPLIT_FILES = [f"split_{i:02d}.txt" for i in range(1, 11)]


@dataclass
class AllSplitFilesExist(Evaluator["FileSplittingTask", AgentRunResult]):
    """Evaluator that checks all 10 split files exist with correct names."""

    async def evaluate(self, ctx: EvaluatorContext["FileSplittingTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all 10 split files exist with correct names."""
        task = ctx.inputs
        split_dir = task.work_dir / "split"

        if not split_dir.exists():
            return EvaluationReason(value=0.0, reason="Directory 'split' not found")

        missing_files = []
        for filename in EXPECTED_SPLIT_FILES:
            file_path = split_dir / filename
            if not file_path.exists():
                missing_files.append(filename)

        if missing_files:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing files: {missing_files}",
            )

        return 1.0


@dataclass
class EqualFileLengths(Evaluator["FileSplittingTask", AgentRunResult]):
    """Evaluator that checks all split files have equal character counts."""

    async def evaluate(self, ctx: EvaluatorContext["FileSplittingTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all split files have equal character counts."""
        task = ctx.inputs
        split_dir = task.work_dir / "split"

        if not split_dir.exists():
            return EvaluationReason(value=0.0, reason="Directory 'split' not found")

        file_lengths = []
        for filename in EXPECTED_SPLIT_FILES:
            file_path = split_dir / filename

            try:
                content = file_path.read_text(encoding="utf-8")
                file_lengths.append(len(content))
            except (OSError, UnicodeDecodeError) as e:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Error reading {filename}: {e}",
                )

        # Check if all lengths are equal
        if len(set(file_lengths)) != 1:
            return EvaluationReason(
                value=0.0,
                reason=f"File lengths are not equal: {file_lengths}",
            )

        return 1.0


@dataclass
class ContentIntegrity(Evaluator["FileSplittingTask", AgentRunResult]):
    """Evaluator that checks concatenated split files equal the original file."""

    async def evaluate(self, ctx: EvaluatorContext["FileSplittingTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that concatenated split files equal the original file."""
        task = ctx.inputs
        split_dir = task.work_dir / "split"
        original_file = task.work_dir / "large_file.txt"

        # Read original content
        try:
            original_content = original_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error reading original file: {e}",
            )

        # Concatenate all split files
        concatenated_content = ""
        for filename in EXPECTED_SPLIT_FILES:
            file_path = split_dir / filename

            try:
                content = file_path.read_text(encoding="utf-8")
                concatenated_content += content
            except (OSError, UnicodeDecodeError) as e:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Error reading {filename}: {e}",
                )

        # Compare content
        if concatenated_content != original_content:
            msg = (
                f"Concatenated content does not match original file. "
                f"Original: {len(original_content)}, "
                f"Concatenated: {len(concatenated_content)}"
            )
            return EvaluationReason(value=0.0, reason=msg)

        return 1.0


@dataclass
class NoExtraFiles(Evaluator["FileSplittingTask", AgentRunResult]):
    """Evaluator that checks no extra files exist in the split directory."""

    async def evaluate(self, ctx: EvaluatorContext["FileSplittingTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that no extra files exist in the split directory."""
        task = ctx.inputs
        split_dir = task.work_dir / "split"

        if not split_dir.exists():
            return EvaluationReason(value=0.0, reason="Directory 'split' not found")

        expected_files = set(EXPECTED_SPLIT_FILES)
        actual_files = {f.name for f in split_dir.iterdir() if f.is_file()}

        extra_files = actual_files - expected_files
        if extra_files:
            return EvaluationReason(
                value=0.0,
                reason=f"Extra files found in split directory: {sorted(extra_files)}",
            )

        return 1.0


class FileSplittingTask(FilesystemTask):
    """Task for splitting a large file into equal-sized smaller files.

    The agent must:
    1. Create a new directory named 'split'
    2. Split large_file.txt into exactly 10 files with equal character counts
    3. Name files as split_01.txt, split_02.txt, ..., split_10.txt
    4. Ensure equal distribution of characters
    5. Preserve content integrity
    """

    name = "file_splitting"
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

You need to split a large text file into multiple smaller files with equal character counts. The task involves \
creating a new directory and splitting the content into exactly 10 files.

### Task Objectives

1. **Create a new directory** named `split` in the test directory
2. **Split the file** `large_file.txt` into exactly 10 files with equal character counts
3. **Name the files** as `split_01.txt`, `split_02.txt`, ..., `split_10.txt` in the `split` directory
4. **Ensure equal distribution** - all split files should have the same number of characters
5. **Preserve content integrity** - concatenating all split files should recreate the original file exactly

### Expected Output

- Directory: `split/`
- Files: `split_01.txt` to `split_10.txt`
- All files should have equal character length
- No loss or modification of content"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            DirectoryExists("split"),
            AllSplitFilesExist(),
            EqualFileLengths(),
            ContentIntegrity(),
            NoExtraFiles(),
        )
