"""Code Locating task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .custom_evaluators import AnswerFormat, FilePathStructure, Zero123GuidanceContent


class CodeLocatingTask(FilesystemTask):
    """Task for finding Zero123 guidance implementation file.

    The agent must:
    1. Explore the ThreeStudio codebase
    2. Identify the file that contains Zero123 guidance implementation
    3. Create answer.txt with the correct file path
    4. The file should contain class Zero123Guidance and @threestudio.register("zero123-guidance")
    """

    name = "code_locating"
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

ThreeStudio is a comprehensive codebase that implements various diffusion-based text-to-3D models, including \
NeRF-based rendering stage and diffusion guidance stage. Your task is to explore the codebase and identify the \
specific file that defines the guidance functionality for the Zero123 model.

### Task Objectives

1. **Explore the ThreeStudio codebase** using filesystem MCP tools
2. **Search through the project structure** to understand the codebase organization
3. **Identify the file** that contains the Zero123 guidance implementation
4. **Create an answer file** with the correct file path

### Expected Output

Create a file named `answer.txt` in the test directory root

**Requirements:**
- Only include the file path, no additional text or explanation
- Use forward slashes (/) for path separators
- Include the full relative path from the project root
- Ensure the path points to the actual file that defines Zero123 guidance

### Success Criteria

The answer file should contain the path to `zero123_guidance.py` which:
- Contains the class `Zero123Guidance`
- Has the decorator `@threestudio.register("zero123-guidance")`
- Is located in the models/guidance directory"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FileExists("answer.txt"),
            AnswerFormat(),
            FilePathStructure(),
            Zero123GuidanceContent(),
        )
