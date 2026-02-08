"""Debugging task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import FileExists, FilePathContains, SingleLineAnswerFormat
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .custom_evaluators import BugFix


class DebuggingTask(FilesystemTask):
    """Task for debugging VoteNet backbone module.

    The agent must:
    1. Examine the codebase to identify the bug
    2. Fix the bug in models/backbone_module.py
    3. Change self.fp2 = PointnetFPModule(mlp=[256,256,256]) to mlp=[512,256,256] or [256+256,256,256]
    4. Create answer.txt with the bug location path
    """

    name = "debugging"

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FileExists("answer.txt"),
            SingleLineAnswerFormat(
                file_path="answer.txt",
                must_contain="models/backbone_module.py",
            ),
            FilePathContains(
                file_path="answer.txt",
                required_components=["models", "backbone_module.py"],
            ),
            BugFix(),
        )
