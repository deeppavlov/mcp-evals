"""Requirements Writing task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import (
    FileExists,
    FileReadable,
    NoDuplicateLines,
    RequiredDependenciesPresent,
    RequirementsFileFormat,
)
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .constants import REQUIRED_DEPS


class RequirementsWritingTask(FilesystemTask):
    """Task for creating requirements.txt file for VoteNet.

    The agent must:
    1. Create requirements.txt file in the main directory
    2. Include all essential dependencies needed to run VoteNet
    3. Ensure file format is correct (one dependency per line)
    4. Include at least: matplotlib, opencv, plyfile, trimesh, pointnet2, networkx
    5. Have at least 3 dependencies and no duplicates
    """

    name = "requirements_writing"

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FileExists("requirements.txt"),
            FileReadable("requirements.txt"),
            RequiredDependenciesPresent("requirements.txt", REQUIRED_DEPS),
            RequirementsFileFormat("requirements.txt", min_lines=3),
            NoDuplicateLines("requirements.txt"),
        )
