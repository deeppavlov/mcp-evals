"""Requirements Writing task for filesystem domain."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.common_evaluators import FileExists, FileReadable
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

REQUIRED_DEPS = ["matplotlib", "opencv", "plyfile", "trimesh", "pointnet2", "networkx"]


@dataclass
class RequiredDependenciesPresent(Evaluator["RequirementsWritingTask", AgentRunResult]):
    """Evaluator that checks all required dependencies are present."""

    async def evaluate(self, ctx: EvaluatorContext["RequirementsWritingTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all required dependencies are present."""
        task = ctx.inputs
        requirements_file = task.work_dir / "requirements.txt"

        try:
            content = requirements_file.read_text(encoding="utf-8")

            missing_deps = []
            found_deps = []

            for dep in REQUIRED_DEPS:
                if dep.lower() in content.lower():
                    found_deps.append(dep)
                else:
                    missing_deps.append(dep)

            if missing_deps:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing required dependencies: {missing_deps}",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking dependencies: {e}")

        return 1.0


@dataclass
class FileFormat(Evaluator["RequirementsWritingTask", AgentRunResult]):
    """Evaluator that checks requirements.txt file has proper format."""

    async def evaluate(self, ctx: EvaluatorContext["RequirementsWritingTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the requirements.txt file has proper format."""
        task = ctx.inputs
        requirements_file = task.work_dir / "requirements.txt"

        try:
            content = requirements_file.read_text(encoding="utf-8")
            lines = content.split("\n")

            if not content.strip():
                return EvaluationReason(value=0.0, reason="File is completely empty")

            non_empty_lines = [line.strip() for line in lines if line.strip()]
            if len(non_empty_lines) < 3:  # noqa: PLR2004
                return EvaluationReason(
                    value=0.0,
                    reason="File seems to have too few dependencies",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking file: {e}")

        return 1.0


@dataclass
class NoDuplicateEntries(Evaluator["RequirementsWritingTask", AgentRunResult]):
    """Evaluator that checks there are no duplicate dependency entries."""

    async def evaluate(self, ctx: EvaluatorContext["RequirementsWritingTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that there are no duplicate dependency entries."""
        task = ctx.inputs
        requirements_file = task.work_dir / "requirements.txt"

        try:
            content = requirements_file.read_text(encoding="utf-8")
            lines = [line.strip().lower() for line in content.split("\n") if line.strip()]

            if len(lines) != len(set(lines)):
                return EvaluationReason(
                    value=0.0,
                    reason="File contains duplicate entries",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking for duplicates: {e}")

        return 1.0


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
            RequiredDependenciesPresent(),
            FileFormat(),
            NoDuplicateEntries(),
        )
