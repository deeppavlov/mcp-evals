"""Find Math Paper task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .custom_evaluators import OriginalFileRemoved


class FindMathPaperTask(FilesystemTask):
    """Task for finding a math-related benchmark paper and renaming it.

    The agent must:
    1. Find a math-related benchmark paper that checks answer correctness
    2. Analyze whether model suffers from insufficient knowledge, lacks generalization, or relies on rote memorization
    3. Rename the corresponding HTML file to answer.html
    """

    name = "find_math_paper"

    def __init__(self, work_dir: Path, fixture: Fixture, tool_retries: int = 1) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture, tool_retries=tool_retries)
        self.evaluators = (
            FileExists("answer.html"),
            OriginalFileRemoved(),
        )
