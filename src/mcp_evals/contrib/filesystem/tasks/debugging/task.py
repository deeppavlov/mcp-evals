"""Debugging task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .custom_evaluators import AnswerFormat, BugFix, FilePathStructure


class DebuggingTask(FilesystemTask):
    """Task for debugging VoteNet backbone module.

    The agent must:
    1. Examine the codebase to identify the bug
    2. Fix the bug in models/backbone_module.py
    3. Change self.fp2 = PointnetFPModule(mlp=[256,256,256]) to mlp=[512,256,256] or [256+256,256,256]
    4. Create answer.txt with the bug location path
    """

    name = "debugging"
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

There is a bug in the VoteNet backbone module that needs to be identified and fixed.

### Task Objectives

1. **Examine the codebase** using filesystem MCP tools
2. **Identify the bug** inside the whole process
3. **Fix the bug** in the code
4. **Create an answer file** with the bug location

### Expected Output

1. **Fix the bug** in the code file directly
2. **Create `answer.txt`** in the test directory root with the format: `path`

**Requirements:**
- Only include the bug's file path in answer.txt
- No additional text or explanation

### Hint

**The bug is not in demo.py**, please look deeper inside the codebase.

### Bug Details

The bug is in `models/backbone_module.py`:
- Line containing `self.fp2 = PointnetFPModule(mlp=[256,256,256])`
- Should be changed to `self.fp2 = PointnetFPModule(mlp=[512,256,256])` or \
`self.fp2 = PointnetFPModule(mlp=[256+256,256,256])`

### Success Criteria

- answer.txt contains the path to models/backbone_module.py
- The bug in the file has been fixed (mlp parameter corrected)"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FileExists("answer.txt"),
            AnswerFormat(),
            FilePathStructure(),
            BugFix(),
        )
