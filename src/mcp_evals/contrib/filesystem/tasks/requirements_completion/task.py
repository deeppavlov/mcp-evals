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
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

The `requirements.txt` file in the ThreeStudio project is used to install necessary Python libraries. \
However, the Zero123-related dependencies were accidentally deleted from the file. Your task is to \
restore these missing dependencies.

### Task Objectives

1. **Locate the requirements.txt file** in the test environment
2. **Identify the missing Zero123 dependencies** that need to be restored
3. **Add the required dependencies** to the requirements.txt file
4. **Ensure the file format is correct** (one dependency per line)

### Required Dependencies to Restore

The following dependencies must be present in requirements.txt:
- einops
- kornia
- taming (taming-transformers-rom1504)
- openai and clip should be on the same line (openai-clip)

### Expected Output

The `requirements.txt` file should:
- Contain all five required dependencies (einops, kornia, taming, openai, clip)
- Have openai and clip on the same line
- Be properly formatted
- Be non-empty and valid

### Success Criteria

- requirements.txt file exists and is readable
- All required dependencies are present
- File format is valid"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FileExists("requirements.txt"),
            FileReadable("requirements.txt"),
            RequiredDependenciesPresent("requirements.txt", REQUIRED_DEPS),
            SpecificDependencyEntries(),
            RequirementsFileFormat("requirements.txt"),
        )
