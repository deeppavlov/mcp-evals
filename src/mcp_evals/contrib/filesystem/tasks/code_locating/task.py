"""Code Locating task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import FileExists, FilePathContains, SingleLineAnswerFormat
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .custom_evaluators import Zero123GuidanceContent


class CodeLocatingTask(FilesystemTask):
    """Task for finding Zero123 guidance implementation file.

    The agent must:
    1. Explore the ThreeStudio codebase
    2. Identify the file that contains Zero123 guidance implementation
    3. Create answer.txt with the correct file path
    4. The file should contain class Zero123Guidance and @threestudio.register("zero123-guidance")
    """

    name = "code_locating"

    def __init__(self, work_dir: Path, fixture: Fixture, tool_retries: int = 1) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture, tool_retries=tool_retries)
        self.evaluators = (
            FileExists("answer.txt"),
            SingleLineAnswerFormat(
                file_path="answer.txt",
                must_be_relative_path=True,
                must_use_forward_slashes=True,
            ),
            FilePathContains(
                file_path="answer.txt",
                required_components=["threestudio", "models", "guidance", "zero123_guidance.py"],
            ),
            Zero123GuidanceContent(),
        )
