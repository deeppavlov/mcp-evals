"""Output Analysis task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .custom_evaluators import FilePath, LineNumbers, RequiredStrings


class OutputAnalysisTask(FilesystemTask):
    """Task for analyzing Zero123 guidance output structure.

    The agent must:
    1. Find the output of guidance_out at line 137 in threestudio/systems/zero123.py
    2. State the structure and where it's found (file and line numbers)
    3. Create answer.txt with four required fields: loss_sds, grad_norm, min_step, max_step
    4. Include line numbers (323-324 and 327-328) and file path
    """

    name = "output_analysis"
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

ThreeStudio is a comprehensive codebase that implements various diffusion-based text-to-3D models, including \
NeRF-based rendering stage and diffusion guidance stage. Your task is to explore the codebase and identify the \
specific file that defines the guidance functionality for the Zero123 model.

### Task

What is the output of `guidance_out`, returned by the code at line 137 in `threestudio/systems/zero123.py`?

Clearly state the structure of it and where you find the answer (file and line numbers). Write your answer in a file \
named `answer.txt` in the test directory root. Do not add extra explanation or formatting beyond what is required by \
the task.

### Expected Output

Create a file named `answer.txt` containing:
- The four required output fields: loss_sds, grad_norm, min_step, max_step
- Line numbers where these fields are defined (lines 323-324 and 327-328)
- The file path: threestudio/models/guidance/zero123_guidance.py

### Success Criteria

The answer file should contain:
- All four strings: "loss_sds", "grad_norm", "min_step", "max_step"
- Line number 323 or 324
- Line number 327 or 328
- The file path "threestudio/models/guidance/zero123_guidance.py\""""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FileExists("answer.txt"),
            RequiredStrings(),
            LineNumbers(),
            FilePath(),
        )
