"""Structure Mirror task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import DirectoryExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.tasks.structure_mirror.constants import MIRROR_DIR_NAME
from mcp_evals.contrib.filesystem.tasks.structure_mirror.custom_evaluators import (
    MirrorStructureCompleteness,
    NoFilesCopied,
)
from mcp_evals.contrib.filesystem.utils import Fixture


class StructureMirrorTask(FilesystemTask):
    """Task for mirroring directory structure with smart placeholders.

    The agent must:
    1. Copy entire directory structure of complex_structure/ to complex_structure_mirror/
    2. Do not copy any file contents, only create directories
    3. In each empty directory, create placeholder.txt with absolute path
    4. Discard directories that directly contain more than 2 files
    5. If directory name contains numbers, append "_processed" to mirror directory name
    """

    name = "structure_mirror"
    goal = """Please use FileSystem tools to finish the following task:

### Task

Copy the entire directory structure of `complex_structure/` to `complex_structure_mirror/`
without copying any file contents. Do not use python code.

### Requirements

- Create the entire directory structure in `complex_structure_mirror/`
- Do not copy any file contents, only create directories
- In each empty directory, create a `placeholder.txt` file containing the absolute path of that directory
- Handle nested directories of any depth
- You should also follow 2 rules:
  1. **Discard any directory that directly contains more than 2 files (only count the immediate folder).**
  2. **If a directory name contains numbers, append "_processed" to the mirror directory name**

### Expected Output

After completing the task:
- `complex_structure_mirror/` directory exists
- All directories from `complex_structure/` are mirrored with modified names (if they contain numbers)
- Directories with more than 2 files are excluded
- Each empty directory contains a `placeholder.txt` file with the absolute path
- No file contents from the source directory are copied"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            DirectoryExists(MIRROR_DIR_NAME),
            NoFilesCopied(),
            MirrorStructureCompleteness(),
        )
