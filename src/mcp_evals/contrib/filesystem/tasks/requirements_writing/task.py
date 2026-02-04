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
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

The VoteNet project is a 3D object detection framework for point clouds. Your task is to create a `requirements.txt` \
file that lists all the necessary Python dependencies for running this codebase.

### Task Objectives

1. **Create a requirements.txt file** in the main directory
2. **Include all essential dependencies** needed to run the VoteNet codebase
3. **Ensure the file format is correct** (one dependency per line)
4. **Save the file as `requirements.txt`** in the current working directory
5. **Not just** pip install or conda install, your answer should contain **every necessary dependencies in the whole \
process of VoteNet**.

### Requirements

The requirements.txt file should contain Python packages that are necessary for:
- 3D point cloud processing
- Deep learning frameworks
- Computer vision libraries
- Data visualization
- 3D mesh processing
- Network/graph operations

### Note

- You can examine the codebase structure and README to understand what packages are needed
- The file should be saved as `requirements.txt` in the current directory
- Each dependency should be on a separate line

### Success Criteria

The requirements.txt file should contain at least these dependencies:
- matplotlib
- opencv
- plyfile
- trimesh
- pointnet2
- networkx

And should have:
- At least 3 dependencies
- No duplicate entries
- Proper file format"""

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
