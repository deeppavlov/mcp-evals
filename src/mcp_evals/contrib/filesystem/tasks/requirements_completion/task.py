"""Requirements Completion task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import (
    FileExists,
    FileReadable,
    RequiredDependenciesPresent,
    RequirementsFileFormat,
)
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .constants import REQUIRED_DEPS
from .custom_evaluators import SpecificDependencyEntries


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

    def __init__(self, work_dir: Path, fixture: Fixture, tool_retries: int = 1) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture, tool_retries=tool_retries)
        self.evaluators = (
            FileExists("requirements.txt"),
            FileReadable("requirements.txt"),
            RequiredDependenciesPresent("requirements.txt", REQUIRED_DEPS),
            SpecificDependencyEntries(),
            RequirementsFileFormat("requirements.txt"),
        )
