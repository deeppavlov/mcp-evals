"""Pattern Matching task for filesystem domain."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.common_evaluators import FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture


def find_30_plus_char_matches(test_dir: Path) -> dict[str, int]:
    """Find all matches with 30 or more characters between files and large_file.txt."""
    large_file = test_dir / "large_file.txt"
    if not large_file.exists():
        return {}

    large_content = large_file.read_text(encoding="utf-8")
    matches: dict[str, int] = {}

    # Check each file from file_01.txt to file_20.txt
    for i in range(1, 21):
        filename = f"file_{i:02d}.txt"
        file_path = test_dir / filename

        if not file_path.exists():
            continue

        file_content = file_path.read_text(encoding="utf-8")

        # Find the longest matching substring (30+ characters)
        longest_match = ""
        longest_match_start = -1

        # Check all possible substrings in the file
        for start_pos in range(len(file_content)):
            for end_pos in range(start_pos + 30, len(file_content) + 1):  # At least 30 characters
                substring = file_content[start_pos:end_pos]

                # Check if this substring exists in large_file.txt
                if substring in large_content and len(substring) > len(longest_match):
                    longest_match = substring
                    # Find the position in large_file.txt where this substring starts
                    large_start_pos = large_content.find(substring)
                    longest_match_start = large_start_pos + 1  # 1-indexed

        # If we found a match of 30+ characters, record it
        if longest_match and len(longest_match) >= 30:  # noqa: PLR2004
            matches[filename] = longest_match_start

    return matches


@dataclass
class AnswerFormat(Evaluator["PatternMatchingTask", AgentRunResult]):
    """Evaluator that checks answer file has correct format."""

    async def evaluate(self, ctx: EvaluatorContext["PatternMatchingTask", AgentRunResult]) -> EvaluatorOutput:  # noqa: PLR0911
        """Verify that the answer file has the correct format."""
        task = ctx.inputs
        answer_file = task.work_dir / "answer.txt"

        if not answer_file.exists():
            return EvaluationReason(value=0.0, reason="File 'answer.txt' not found")

        try:
            content = answer_file.read_text(encoding="utf-8").strip()

            # If file is empty, that's acceptable (no matches found)
            if not content:
                return 1.0

            lines = content.split("\n")

            for i, line in enumerate(lines, 1):
                line_ = line.strip()
                if not line_:
                    continue

                # Check format: filename.txt,start_position
                parts = line_.split(",")
                if len(parts) != 2:  # noqa: PLR2004
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Line {i} has incorrect format '{line_}'. Expected format: filename.txt,start_position",
                    )

                filename, start_pos = parts

                # Check filename format
                if not filename.endswith(".txt") or not filename.startswith("file_"):
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Line {i} has invalid filename: '{filename}'",
                    )

                # Check position format (should be integer)
                try:
                    start_int = int(start_pos)
                    if start_int <= 0:
                        return EvaluationReason(
                            value=0.0,
                            reason=f"Line {i} has invalid position: {start_pos}",
                        )
                except ValueError:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Line {i} has non-integer position: '{start_pos}'",
                    )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error reading answer file: {e}")

        return 1.0


@dataclass
class FilesExist(Evaluator["PatternMatchingTask", AgentRunResult]):
    """Evaluator that checks all files mentioned in answer.txt actually exist."""

    async def evaluate(self, ctx: EvaluatorContext["PatternMatchingTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all files mentioned in answer.txt actually exist."""
        task = ctx.inputs
        answer_file = task.work_dir / "answer.txt"

        if not answer_file.exists():
            return EvaluationReason(value=0.0, reason="File 'answer.txt' not found")

        try:
            content = answer_file.read_text(encoding="utf-8").strip()

            if not content:
                return 1.0  # No files to verify

            lines = content.split("\n")
            for line in lines:
                line_ = line.strip()
                if not line_:
                    continue

                filename = line_.split(",")[0]
                file_path = task.work_dir / filename

                if not file_path.exists():
                    return EvaluationReason(
                        value=0.0,
                        reason=f"File mentioned in answer does not exist: {filename}",
                    )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying file existence: {e}")

        return 1.0


@dataclass
class MatchLengthIs30Plus(Evaluator["PatternMatchingTask", AgentRunResult]):
    """Evaluator that checks all matches are at least 30 characters long."""

    async def evaluate(self, ctx: EvaluatorContext["PatternMatchingTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all matches are at least 30 characters long."""
        task = ctx.inputs
        answer_file = task.work_dir / "answer.txt"

        if not answer_file.exists():
            return EvaluationReason(value=0.0, reason="File 'answer.txt' not found")

        try:
            content = answer_file.read_text(encoding="utf-8").strip()

            if not content:
                return 1.0  # No matches to verify

            large_file = task.work_dir / "large_file.txt"
            large_content = large_file.read_text(encoding="utf-8")

            lines = content.split("\n")
            for line in lines:
                line_ = line.strip()
                if not line_:
                    continue

                filename, start_pos = line_.split(",")
                start_int = int(start_pos)

                # Get the file content to check the match
                file_path = task.work_dir / filename
                file_content = file_path.read_text(encoding="utf-8")

                # Find the longest matching substring starting from the given position
                longest_match = ""
                # At least 30 characters
                for end_pos in range(start_int + 30 - 1, len(large_content) + 1):
                    # Convert to 0-indexed
                    substring = large_content[start_int - 1 : end_pos]
                    if substring in file_content:
                        longest_match = substring
                    else:
                        break

                if len(longest_match) < 30:  # noqa: PLR2004
                    msg = f"Match in {filename} is {len(longest_match)} characters, less than 30"
                    return EvaluationReason(value=0.0, reason=msg)

        except (ValueError, OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying match lengths: {e}")

        return 1.0


@dataclass
class MatchesAreCorrect(Evaluator["PatternMatchingTask", AgentRunResult]):
    """Evaluator that checks matches found in answer.txt are actually correct."""

    async def evaluate(self, ctx: EvaluatorContext["PatternMatchingTask", AgentRunResult]) -> EvaluatorOutput:  # noqa: C901, PLR0911
        """Verify that the matches found in answer.txt are actually correct."""
        task = ctx.inputs
        answer_file = task.work_dir / "answer.txt"

        if not answer_file.exists():
            return EvaluationReason(value=0.0, reason="File 'answer.txt' not found")

        try:
            content = answer_file.read_text(encoding="utf-8").strip()

            # If no content, check if there should actually be no matches
            if not content:
                expected_matches = find_30_plus_char_matches(task.work_dir)
                if expected_matches:
                    msg = f"Answer file is empty but matches should exist: {list(expected_matches.keys())}"
                    return EvaluationReason(value=0.0, reason=msg)
                return 1.0

            # Parse answer file
            answer_matches: dict[str, int] = {}
            lines = content.split("\n")
            for line in lines:
                line_ = line.strip()
                if not line_:
                    continue
                filename, start_pos = line_.split(",")
                answer_matches[filename] = int(start_pos)

            # Get expected matches
            expected_matches = find_30_plus_char_matches(task.work_dir)

            # Check if all answer matches are correct
            for filename, start_pos in answer_matches.items():
                if filename not in expected_matches:
                    msg = f"File {filename} listed in answer but has no valid 30+ character match"
                    return EvaluationReason(value=0.0, reason=msg)

                expected_start = expected_matches[filename]
                if start_pos != expected_start:
                    msg = f"Incorrect match position for {filename}. Expected: {expected_start}, Found: {start_pos}"
                    return EvaluationReason(value=0.0, reason=msg)

            # Check if all expected matches are in answer
            for filename in expected_matches:
                if filename not in answer_matches:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Missing match for {filename} in answer file",
                    )

        except (ValueError, OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying matches: {e}")

        return 1.0


class PatternMatchingTask(FilesystemTask):
    """Task for finding files with common substrings of 30+ characters.

    The agent must:
    1. Read the reference file large_file.txt
    2. Examine each file from file_01.txt to file_20.txt
    3. Find files with substrings of 30+ characters matching large_file.txt
    4. Create answer.txt with results in format: filename.txt,start_position
    """

    name = "pattern_matching"
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

Your task is to find all files that contain a substring of 30 or more characters that also appears in `large_file.txt`.\
 **You are not allowed to use python code.**

### Task Objectives

1. **Read the reference file** `large_file.txt` to understand its content
2. **Examine each file** from file_01.txt to file_20.txt
3. **Find files** that contain a substring of 30 or more characters that matches a substring in `large_file.txt`
4. **Create a file `answer.txt`** and write the results to it with the following format:
   - One line per matching file
   - Format: `filename.txt,start_position`
   - Where start_position is the character position (1-indexed) of the matching substring in `large_file.txt`
   - Do not add any things else other than `filename.txt,start_position`

### Expected Output

- File name: `answer.txt`
- Format: Each line should be `filename.txt,start_position`
- Only include files with matches of 30+ characters
- Position should be 1-indexed (first character is position 1)"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FileExists("answer.txt"),
            AnswerFormat(),
            FilesExist(),
            MatchLengthIs30Plus(),
            MatchesAreCorrect(),
        )
