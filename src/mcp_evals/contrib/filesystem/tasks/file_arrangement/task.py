"""File Arrangement task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import DirectoriesExist, DirectoryExists, FilesExistInDirectory
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .constants import REQUIRED_FILE_MAPPING, REQUIRED_FOLDERS
from .custom_evaluators import NoDuplicateRequiredFiles, RequiredFilesInCorrectFolders


class FileArrangementTask(FilesystemTask):
    """Task for organizing files into structured folder system.

    The agent must:
    1. Create folders: work/, life/, archives/, temp/, others/
    2. Move files to their designated locations according to organization scheme
    3. Ensure all 18 required files are in correct folders
    4. Ensure no duplicate required files
    """

    name = "file_arrangement"

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            DirectoriesExist(REQUIRED_FOLDERS),
            FilesExistInDirectory("work", REQUIRED_FILE_MAPPING["work"]),
            FilesExistInDirectory("life", REQUIRED_FILE_MAPPING["life"]),
            FilesExistInDirectory("archives", REQUIRED_FILE_MAPPING["archives"]),
            FilesExistInDirectory("temp", REQUIRED_FILE_MAPPING["temp"]),
            DirectoryExists("others"),
            RequiredFilesInCorrectFolders(),
            NoDuplicateRequiredFiles(),
        )
