"""Uppercase task for filesystem domain."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.common_evaluators import DirectoryExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

# Expected word counts based on answer.md
# Special case: file_06.txt can be 21 or 22
EXPECTED_COUNTS = [22, 22, 22, 22, 18, 22, 22, 22, 18, 20]

# Expected files
EXPECTED_FILES = [f"file_{i:02d}.txt" for i in range(1, 11)]


@dataclass
class UppercaseDirectoryExists(Evaluator["UppercaseTask", AgentRunResult]):
    """Evaluator that checks uppercase directory exists."""

    async def evaluate(self, ctx: EvaluatorContext["UppercaseTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the uppercase directory exists."""
        task = ctx.inputs
        uppercase_dir = task.work_dir / "uppercase"

        if not uppercase_dir.exists():
            return EvaluationReason(value=0.0, reason="Directory 'uppercase' not found")

        if not uppercase_dir.is_dir():
            return EvaluationReason(value=0.0, reason="'uppercase' exists but is not a directory")

        return 1.0


@dataclass
class UppercaseFilesExist(Evaluator["UppercaseTask", AgentRunResult]):
    """Evaluator that checks all 10 uppercase files exist."""

    async def evaluate(self, ctx: EvaluatorContext["UppercaseTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all 10 uppercase files exist."""
        task = ctx.inputs
        uppercase_dir = task.work_dir / "uppercase"

        if not uppercase_dir.exists():
            return EvaluationReason(value=0.0, reason="Directory 'uppercase' not found")

        for filename in EXPECTED_FILES:
            file_path = uppercase_dir / filename

            if not file_path.exists():
                return EvaluationReason(
                    value=0.0,
                    reason=f"File '{filename}' not found in uppercase directory",
                )

        return 1.0


@dataclass
class UppercaseContent(Evaluator["UppercaseTask", AgentRunResult]):
    """Evaluator that checks uppercase files contain correct uppercase content."""

    async def evaluate(self, ctx: EvaluatorContext["UppercaseTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that uppercase files contain the correct uppercase content."""
        task = ctx.inputs
        uppercase_dir = task.work_dir / "uppercase"

        for filename in EXPECTED_FILES:
            original_file = task.work_dir / filename
            uppercase_file = uppercase_dir / filename

            if not original_file.exists():
                return EvaluationReason(
                    value=0.0,
                    reason=f"Original file '{filename}' not found",
                )

            try:
                original_content = original_file.read_text(encoding="utf-8")
                uppercase_content = uppercase_file.read_text(encoding="utf-8")

                # Check if uppercase content is the uppercase version of original
                expected_uppercase = original_content.upper()

                if uppercase_content != expected_uppercase:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"File '{filename}' content is not properly converted to uppercase",
                    )

            except (OSError, UnicodeDecodeError) as e:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Error reading file '{filename}': {e}",
                )

        return 1.0


@dataclass
class AnswerFileExists(Evaluator["UppercaseTask", AgentRunResult]):
    """Evaluator that checks answer.txt file exists in uppercase directory."""

    async def evaluate(self, ctx: EvaluatorContext["UppercaseTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the answer.txt file exists in the uppercase directory."""
        task = ctx.inputs
        uppercase_dir = task.work_dir / "uppercase"
        answer_file = uppercase_dir / "answer.txt"

        if not answer_file.exists():
            return EvaluationReason(
                value=0.0,
                reason="File 'answer.txt' not found in uppercase directory",
            )

        return 1.0


@dataclass
class AnswerFormat(Evaluator["UppercaseTask", AgentRunResult]):
    """Evaluator that checks answer file has correct format."""

    async def evaluate(self, ctx: EvaluatorContext["UppercaseTask", AgentRunResult]) -> EvaluatorOutput:  # noqa: C901, PLR0911
        """Verify that the answer file has the correct format."""
        task = ctx.inputs
        uppercase_dir = task.work_dir / "uppercase"
        answer_file = uppercase_dir / "answer.txt"

        if not answer_file.exists():
            return EvaluationReason(value=0.0, reason="File 'answer.txt' not found")

        try:
            content = answer_file.read_text(encoding="utf-8").strip()

            if not content:
                return EvaluationReason(value=0.0, reason="Answer file is empty")

            lines = content.split("\n")

            # Check if we have exactly 10 lines
            if len(lines) != 10:  # noqa: PLR2004
                return EvaluationReason(
                    value=0.0,
                    reason=f"Answer file has {len(lines)} lines, expected 10",
                )

            for i, line in enumerate(lines, 1):
                line_ = line.strip()
                if not line_:
                    return EvaluationReason(value=0.0, reason=f"Line {i} is empty")

                # Check format: filename:word_count
                if ":" not in line_:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Line {i} has incorrect format: '{line_}'. Expected format: filename:word_count",
                    )

                parts = line_.split(":", 1)
                if len(parts) != 2:  # noqa: PLR2004
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Line {i} has incorrect format: '{line_}'. Expected format: filename:word_count",
                    )

                filename, word_count_str = parts

                # Check filename format
                if not filename.endswith(".txt") or not filename.startswith("file_"):
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Line {i} has invalid filename: '{filename}'",
                    )

                # Check word count format (should be integer)
                try:
                    word_count = int(word_count_str)
                    if word_count <= 0:
                        return EvaluationReason(
                            value=0.0,
                            reason=f"Line {i} has invalid word count: {word_count_str}",
                        )
                except ValueError:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Line {i} has non-integer word count: '{word_count_str}'",
                    )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error reading answer file: {e}")

        return 1.0


@dataclass
class AllFilesAreIncluded(Evaluator["UppercaseTask", AgentRunResult]):
    """Evaluator that checks all 10 files are included in the answer."""

    async def evaluate(self, ctx: EvaluatorContext["UppercaseTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all 10 files are included in the answer."""
        task = ctx.inputs
        uppercase_dir = task.work_dir / "uppercase"
        answer_file = uppercase_dir / "answer.txt"

        if not answer_file.exists():
            return EvaluationReason(value=0.0, reason="File 'answer.txt' not found")

        try:
            content = answer_file.read_text(encoding="utf-8").strip()
            lines = content.split("\n")

            # Check that all 10 files are present
            found_files = set()
            for line in lines:
                parts = line.split(":", 1)
                filename = parts[0]
                found_files.add(filename)

            expected_files = set(EXPECTED_FILES)

            if found_files != expected_files:
                missing = expected_files - found_files
                extra = found_files - expected_files
                msg_parts = []
                if missing:
                    msg_parts.append(f"Missing files: {sorted(missing)}")
                if extra:
                    msg_parts.append(f"Extra files: {sorted(extra)}")
                return EvaluationReason(value=0.0, reason=", ".join(msg_parts))

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying file inclusion: {e}")

        return 1.0


@dataclass
class WordCountsAreCorrect(Evaluator["UppercaseTask", AgentRunResult]):
    """Evaluator that checks word counts in answer.txt are correct."""

    async def evaluate(self, ctx: EvaluatorContext["UppercaseTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the word counts in answer.txt are correct."""
        task = ctx.inputs
        uppercase_dir = task.work_dir / "uppercase"
        answer_file = uppercase_dir / "answer.txt"

        if not answer_file.exists():
            return EvaluationReason(value=0.0, reason="File 'answer.txt' not found")

        try:
            content = answer_file.read_text(encoding="utf-8").strip()
            lines = content.split("\n")

            # Create a set of expected file entries for easier checking
            expected_entries = set()
            for i in range(1, 11):
                filename = f"file_{i:02d}.txt"
                expected_count = EXPECTED_COUNTS[i - 1]
                if i == 6:  # Special case for file_06.txt: can be 21 or 22  # noqa: PLR2004
                    expected_entries.add(f"{filename}:21")
                    expected_entries.add(f"{filename}:22")
                else:
                    expected_entries.add(f"{filename}:{expected_count}")

            # Check each line in the answer file
            found_entries = set()
            for line in lines:
                line_ = line.strip()
                if line_ in expected_entries:
                    found_entries.add(line_)
                else:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Invalid entry: {line_}",
                    )

            # Check if we found all expected entries
            if len(found_entries) != 10:  # noqa: PLR2004
                missing = expected_entries - found_entries
                msg = f"Found {len(found_entries)} entries, expected 10"
                if missing:
                    msg += f". Missing entries: {sorted(missing)}"
                return EvaluationReason(value=0.0, reason=msg)

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying word counts: {e}")

        return 1.0


class UppercaseTask(FilesystemTask):
    """Task for converting files to uppercase and counting words.

    The agent must:
    1. Create an uppercase directory
    2. Convert each file from file_01.txt to file_10.txt to uppercase
    3. Save converted files in uppercase/ directory
    4. Count words in each original file
    5. Create answer.txt with word counts in specified format
    """

    name = "uppercase"
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

You need to process 10 text files (file_01.txt to file_10.txt) and convert their content to uppercase format.

### Task Objectives

1. **Create an uppercase directory** in the test environment root
2. **Convert each file** from file_01.txt to file_10.txt to uppercase
3. **Save converted files** in the uppercase/ directory with the same names
4. **Count words** in each original file (file_01.txt to file_10.txt)
5. **Create answer.txt** with word counts in the specified format

### Specified Format of answer.txt

Create a file named `answer.txt` in the `uppercase/` directory

**Requirements:**

- Each line should follow the format: `<filename>:<word_count>`
- Include all 10 files: file_01.txt, file_02.txt, ..., file_10.txt
- Use the exact filename format (file_01.txt, file_02.txt, etc.)
- One entry per line
- Total of 10 lines

### Expected Output

- Directory: `uppercase/`
- Files: `file_01.txt` to `file_10.txt` (all in uppercase)
- File: `uppercase/answer.txt` with word counts"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            DirectoryExists("uppercase"),
            UppercaseFilesExist(),
            UppercaseContent(),
            AnswerFileExists(),
            AnswerFormat(),
            AllFilesAreIncluded(),
            WordCountsAreCorrect(),
        )
