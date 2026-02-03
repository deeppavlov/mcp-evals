"""Project Management task for filesystem domain."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

# Expected files in each directory
EXPECTED_PYTHON_FILES = [
    "study_notes.py",
    "model.py",
    "data_analysis.py",
    "travel_calculator.py",
    "inventory.py",
    "playlist_manager.py",
]

EXPECTED_CSV_FILES = [
    "learning_progress.csv",
    "weekly_schedule.csv",
    "results_record.csv",
    "september_summary.csv",
    "data.csv",
    "favorite_songs.csv",
    "travel_itinerary.csv",
]

EXPECTED_LEARNING_FILES = [
    "learning_roadmap.md",
    "research_topics.md",
    "experiment_summary.md",
    "exp_record.md",
    "README.md",
    "analysis_report.md",
    "learning_goals.md",
]

EXPECTED_ENTERTAINMENT_FILES = [
    "gaming_schedule.md",
    "entertainment_planner.md",
    "travel_bucket_list.md",
]

EXPECTED_MUSIC_FILES = [
    "music_collection.md",
]

# Required directory structure
REQUIRED_DIRS = [
    "experiments",
    "experiments/ml_projects",
    "experiments/data_analysis",
    "learning",
    "learning/progress_tracking",
    "learning/resources",
    "personal",
    "personal/entertainment",
    "personal/collections",
]

# Expected file counts
EXPECTED_COUNTS = {
    "experiments/ml_projects": 6,
    "experiments/data_analysis": 7,
    "learning/resources": 7,
    "learning/progress_tracking": 0,
    "personal/entertainment": 3,
    "personal/collections": 1,
}


@dataclass
class OrganizedProjectsDirectoryExists(Evaluator["ProjectManagementTask", AgentRunResult]):
    """Evaluator that checks organized_projects directory exists."""

    async def evaluate(self, ctx: EvaluatorContext["ProjectManagementTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the organized_projects directory exists."""
        task = ctx.inputs
        organized_dir = task.work_dir / "organized_projects"

        if not organized_dir.exists():
            return EvaluationReason(value=0.0, reason="'organized_projects' directory not found")

        if not organized_dir.is_dir():
            return EvaluationReason(value=0.0, reason="'organized_projects' exists but is not a directory")

        return 1.0


@dataclass
class DirectoryStructure(Evaluator["ProjectManagementTask", AgentRunResult]):
    """Evaluator that checks all required subdirectories exist."""

    async def evaluate(self, ctx: EvaluatorContext["ProjectManagementTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all required subdirectories exist."""
        task = ctx.inputs
        organized_dir = task.work_dir / "organized_projects"

        missing_dirs = []
        for dir_path in REQUIRED_DIRS:
            full_path = organized_dir / dir_path
            if not full_path.exists():
                missing_dirs.append(dir_path)
            elif not full_path.is_dir():
                missing_dirs.append(f"{dir_path} (not a directory)")

        if missing_dirs:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing or invalid directories: {missing_dirs}",
            )

        return 1.0


@dataclass
class PythonFilesInMLProjects(Evaluator["ProjectManagementTask", AgentRunResult]):
    """Evaluator that checks all Python files are moved to experiments/ml_projects."""

    async def evaluate(self, ctx: EvaluatorContext["ProjectManagementTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all Python files are moved to experiments/ml_projects."""
        task = ctx.inputs
        organized_dir = task.work_dir / "organized_projects"
        ml_projects_dir = organized_dir / "experiments" / "ml_projects"

        missing_files = []
        for filename in EXPECTED_PYTHON_FILES:
            file_path = ml_projects_dir / filename
            if not file_path.exists():
                missing_files.append(filename)

        if missing_files:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing Python files in ml_projects: {missing_files}",
            )

        return 1.0


@dataclass
class CSVFilesInDataAnalysis(Evaluator["ProjectManagementTask", AgentRunResult]):
    """Evaluator that checks all CSV files are moved to experiments/data_analysis."""

    async def evaluate(self, ctx: EvaluatorContext["ProjectManagementTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all CSV files are moved to experiments/data_analysis."""
        task = ctx.inputs
        organized_dir = task.work_dir / "organized_projects"
        data_analysis_dir = organized_dir / "experiments" / "data_analysis"

        missing_files = []
        for filename in EXPECTED_CSV_FILES:
            file_path = data_analysis_dir / filename
            if not file_path.exists():
                missing_files.append(filename)

        if missing_files:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing CSV files in data_analysis: {missing_files}",
            )

        return 1.0


@dataclass
class LearningMDFilesInResources(Evaluator["ProjectManagementTask", AgentRunResult]):
    """Evaluator that checks learning-related markdown files are moved to learning/resources."""

    async def evaluate(self, ctx: EvaluatorContext["ProjectManagementTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that learning-related markdown files are moved to learning/resources."""
        task = ctx.inputs
        organized_dir = task.work_dir / "organized_projects"
        resources_dir = organized_dir / "learning" / "resources"

        missing_files = []
        for filename in EXPECTED_LEARNING_FILES:
            file_path = resources_dir / filename
            if not file_path.exists():
                missing_files.append(filename)

        if missing_files:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing learning markdown files in resources: {missing_files}",
            )

        return 1.0


@dataclass
class EntertainmentMDFilesInEntertainment(Evaluator["ProjectManagementTask", AgentRunResult]):
    """Evaluator that checks entertainment planning markdown files are moved to personal/entertainment."""

    async def evaluate(self, ctx: EvaluatorContext["ProjectManagementTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that entertainment planning markdown files are moved to personal/entertainment."""
        task = ctx.inputs
        organized_dir = task.work_dir / "organized_projects"
        entertainment_dir = organized_dir / "personal" / "entertainment"

        missing_files = []
        for filename in EXPECTED_ENTERTAINMENT_FILES:
            file_path = entertainment_dir / filename
            if not file_path.exists():
                missing_files.append(filename)

        if missing_files:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing entertainment markdown files in entertainment: {missing_files}",
            )

        return 1.0


@dataclass
class MusicMDFilesInCollections(Evaluator["ProjectManagementTask", AgentRunResult]):
    """Evaluator that checks music collection markdown files are moved to personal/collections."""

    async def evaluate(self, ctx: EvaluatorContext["ProjectManagementTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that music collection markdown files are moved to personal/collections."""
        task = ctx.inputs
        organized_dir = task.work_dir / "organized_projects"
        collections_dir = organized_dir / "personal" / "collections"

        missing_files = []
        for filename in EXPECTED_MUSIC_FILES:
            file_path = collections_dir / filename
            if not file_path.exists():
                missing_files.append(filename)

        if missing_files:
            return EvaluationReason(
                value=0.0,
                reason=f"Missing music collection markdown files in collections: {missing_files}",
            )

        return 1.0


@dataclass
class ProgressTrackingEmpty(Evaluator["ProjectManagementTask", AgentRunResult]):
    """Evaluator that checks progress_tracking directory is empty."""

    async def evaluate(self, ctx: EvaluatorContext["ProjectManagementTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that progress_tracking directory is empty."""
        task = ctx.inputs
        organized_dir = task.work_dir / "organized_projects"
        progress_dir = organized_dir / "learning" / "progress_tracking"

        try:
            files_in_progress = list(progress_dir.iterdir())
            if files_in_progress:
                file_names = [f.name for f in files_in_progress]
                msg = f"progress_tracking directory should be empty, but contains: {file_names}"
                return EvaluationReason(value=0.0, reason=msg)
        except (OSError, PermissionError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error checking progress_tracking directory: {e}",
            )

        return 1.0


@dataclass
class ProjectStructureFileExists(Evaluator["ProjectManagementTask", AgentRunResult]):
    """Evaluator that checks project_structure.md file exists."""

    async def evaluate(self, ctx: EvaluatorContext["ProjectManagementTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that project_structure.md file exists."""
        task = ctx.inputs
        organized_dir = task.work_dir / "organized_projects"
        structure_file = organized_dir / "project_structure.md"

        if not structure_file.exists():
            return EvaluationReason(value=0.0, reason="'project_structure.md' file not found")

        if not structure_file.is_file():
            return EvaluationReason(value=0.0, reason="'project_structure.md' exists but is not a file")

        return 1.0


@dataclass
class FileCounts(Evaluator["ProjectManagementTask", AgentRunResult]):
    """Evaluator that checks each directory has the correct number of files."""

    async def evaluate(self, ctx: EvaluatorContext["ProjectManagementTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that each directory has the correct number of files."""
        task = ctx.inputs
        organized_dir = task.work_dir / "organized_projects"

        incorrect_counts = []
        for dir_path, expected_count in EXPECTED_COUNTS.items():
            full_path = organized_dir / dir_path
            try:
                actual_count = len([f for f in full_path.iterdir() if f.is_file()])

                if actual_count != expected_count:
                    incorrect_counts.append(
                        f"{dir_path}: expected {expected_count}, got {actual_count}",
                    )
            except (OSError, PermissionError):
                incorrect_counts.append(f"{dir_path}: error reading directory")

        if incorrect_counts:
            return EvaluationReason(
                value=0.0,
                reason=f"Incorrect file counts: {incorrect_counts}",
            )

        return 1.0


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
    goal = """Please use FileSystem tools to finish the following task:

1. **Create the main directory structure** in `desktop_2`:

   - Create a new directory in main directory called `organized_projects`
   - Inside `organized_projects`, create 3 main subdirectories: `experiments`, `learning`, and `personal`
   - Inside `experiments`, create 2 subdirectories: `ml_projects` and `data_analysis`
   - Inside `learning`, create 2 subdirectories: `progress_tracking` and `resources`
   - Inside `personal`, create 2 subdirectories: `entertainment` and `collections`

2. **Move all the Python files** to `experiments/ml_projects/`:

3. **Move all the CSV files** to `experiments/data_analysis/`:

4. **Only Move learning-related markdown files** to `learning/resources/`:

5. **Only Move entertainment planning-related markdown files** to `personal/entertainment/`:

6. **Only Move music collection-related markdown files** to `personal/collections/`:

7. **step 4.5.6 should move all the markdown files.**

8. **Create a project structure documentation file**:

   - Create `project_structure.md` in the `organized_projects` directory
   - Document the new organization with exact file counts for each subdirectory
   - Include a summary of what types of files are in each directory"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            OrganizedProjectsDirectoryExists(),
            DirectoryStructure(),
            PythonFilesInMLProjects(),
            CSVFilesInDataAnalysis(),
            LearningMDFilesInResources(),
            EntertainmentMDFilesInEntertainment(),
            MusicMDFilesInCollections(),
            ProgressTrackingEmpty(),
            ProjectStructureFileExists(),
            FileCounts(),
        )
