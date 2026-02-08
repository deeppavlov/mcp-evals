"""Project Management task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import (
    DirectoriesExist,
    DirectoryEmpty,
    DirectoryExists,
    DirectoryFileCounts,
    FileExists,
    FilesExistInDirectory,
)
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .constants import (
    EXPECTED_COUNTS,
    EXPECTED_CSV_FILES,
    EXPECTED_ENTERTAINMENT_FILES,
    EXPECTED_LEARNING_FILES,
    EXPECTED_MUSIC_FILES,
    EXPECTED_PYTHON_FILES,
    REQUIRED_DIRS,
)


class ProjectManagementTask(FilesystemTask):
    """Task for reorganizing files into a structured directory hierarchy.

    The agent must:
    1. Create organized_projects directory with subdirectories
    2. Move Python files to experiments/ml_projects/
    3. Move CSV files to experiments/data_analysis/
    4. Move learning markdown files to learning/resources/
    5. Move entertainment markdown files to personal/entertainment/
    6. Move music collection markdown files to personal/collections/
    7. Create project_structure.md documentation
    """

    name = "project_management"

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            DirectoryExists("organized_projects"),
            DirectoriesExist(REQUIRED_DIRS, base_path="organized_projects"),
            FilesExistInDirectory("organized_projects/experiments/ml_projects", EXPECTED_PYTHON_FILES),
            FilesExistInDirectory("organized_projects/experiments/data_analysis", EXPECTED_CSV_FILES),
            FilesExistInDirectory("organized_projects/learning/resources", EXPECTED_LEARNING_FILES),
            FilesExistInDirectory("organized_projects/personal/entertainment", EXPECTED_ENTERTAINMENT_FILES),
            FilesExistInDirectory("organized_projects/personal/collections", EXPECTED_MUSIC_FILES),
            DirectoryEmpty("organized_projects/learning/progress_tracking"),
            FileExists("organized_projects/project_structure.md"),
            DirectoryFileCounts(EXPECTED_COUNTS, base_path="organized_projects"),
        )
