"""Dataset Comparison task for filesystem domain."""

import re
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.common_evaluators import FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

REQUIRED_CATEGORIES = {
    "chair",
    "table",
    "bed",
    "bookshelf",
    "desk",
    "toilet",
    "dresser",
    "bathtub",
    "sofa",
    "night_stand",
}

EXPECTED_COUNTS = {
    "chair": 4681,
    "table": 1170,
    "bed": 370,
    "bookshelf": 377,
    "desk": 680,
    "toilet": 256,
    "dresser": 213,
    "bathtub": 144,
    "sofa": 1,
    "night_stand": 224,
}


@dataclass
class AnalysisFileExists(Evaluator["DatasetComparisonTask", AgentRunResult]):
    """Evaluator that checks analysis.txt file exists."""

    async def evaluate(self, ctx: EvaluatorContext["DatasetComparisonTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the analysis.txt file exists."""
        task = ctx.inputs
        analysis_file = task.work_dir / "analysis.txt"

        if not analysis_file.exists():
            return EvaluationReason(value=0.0, reason="File 'analysis.txt' not found")

        return 1.0


@dataclass
class FileLocation(Evaluator["DatasetComparisonTask", AgentRunResult]):
    """Evaluator that checks analysis.txt file is in correct location."""

    async def evaluate(self, ctx: EvaluatorContext["DatasetComparisonTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the analysis.txt file is in the correct location."""
        task = ctx.inputs
        analysis_file = task.work_dir / "analysis.txt"

        if analysis_file.parent != task.work_dir:
            return EvaluationReason(
                value=0.0,
                reason="Analysis file should be in the test directory root",
            )

        return 1.0


@dataclass
class AnalysisFormat(Evaluator["DatasetComparisonTask", AgentRunResult]):
    """Evaluator that checks analysis file has correct format."""

    async def evaluate(self, ctx: EvaluatorContext["DatasetComparisonTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the analysis file has the correct format."""
        task = ctx.inputs
        analysis_file = task.work_dir / "analysis.txt"

        try:
            content = analysis_file.read_text(encoding="utf-8")
            lines = content.split("\n")

            if not content.strip():
                return EvaluationReason(value=0.0, reason="Analysis file is empty")

            if len(lines) < 2:
                return EvaluationReason(
                    value=0.0,
                    reason="Analysis file doesn't have enough lines for a category block",
                )

            line_index = 0
            block_count = 0

            while line_index < len(lines):
                while line_index < len(lines) and lines[line_index].strip() == "":
                    line_index += 1

                if line_index >= len(lines):
                    break

                if line_index + 1 >= len(lines):
                    return EvaluationReason(
                        value=0.0,
                        reason="Incomplete category block at the end",
                    )

                category_line = lines[line_index].strip()
                if not category_line:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Empty category name at line {line_index + 1}",
                    )

                count_line = lines[line_index + 1].strip()
                if not count_line:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Empty count at line {line_index + 2}",
                    )

                if not re.search(r"\d+", count_line):
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Count line doesn't contain a number at line {line_index + 2}: '{count_line}'",
                    )

                block_count += 1
                line_index += 2

                if line_index < len(lines) and lines[line_index].strip() == "":
                    line_index += 1

            if block_count == 0:
                return EvaluationReason(value=0.0, reason="No valid category blocks found")

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error reading analysis file: {e}")

        return 1.0


@dataclass
class RequiredCategories(Evaluator["DatasetComparisonTask", AgentRunResult]):
    """Evaluator that checks all required SUN RGB-D categories are present."""

    async def evaluate(self, ctx: EvaluatorContext["DatasetComparisonTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all required SUN RGB-D categories are present."""
        task = ctx.inputs
        analysis_file = task.work_dir / "analysis.txt"

        try:
            content = analysis_file.read_text(encoding="utf-8")
            lines = content.split("\n")

            categories_found = []
            line_index = 0

            while line_index < len(lines):
                while line_index < len(lines) and lines[line_index].strip() == "":
                    line_index += 1

                if line_index >= len(lines):
                    break

                category_line = lines[line_index].strip()
                if category_line:
                    categories_found.append(category_line.lower())

                line_index += 2
                while line_index < len(lines) and lines[line_index].strip() == "":
                    line_index += 1

            missing_categories = REQUIRED_CATEGORIES - set(categories_found)
            if missing_categories:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing required categories: {sorted(missing_categories)}",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying required categories: {e}")

        return 1.0


@dataclass
class CategoryCounts(Evaluator["DatasetComparisonTask", AgentRunResult]):
    """Evaluator that checks category counts match expected values."""

    async def evaluate(self, ctx: EvaluatorContext["DatasetComparisonTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the category counts match the expected values."""
        task = ctx.inputs
        analysis_file = task.work_dir / "analysis.txt"

        try:
            content = analysis_file.read_text(encoding="utf-8")
            lines = content.split("\n")

            category_counts = {}
            line_index = 0

            while line_index < len(lines):
                while line_index < len(lines) and lines[line_index].strip() == "":
                    line_index += 1

                if line_index >= len(lines):
                    break

                category_line = lines[line_index].strip()
                if not category_line:
                    line_index += 1
                    continue

                if line_index + 1 < len(lines):
                    count_line = lines[line_index + 1].strip()
                    if count_line:
                        count_match = re.search(r"(\d+)", count_line)
                        if count_match:
                            category = category_line.lower()
                            count = int(count_match.group(1))
                            category_counts[category] = count

                line_index += 2
                while line_index < len(lines) and lines[line_index].strip() == "":
                    line_index += 1

            for category, expected_count in EXPECTED_COUNTS.items():
                if category in category_counts:
                    actual_count = category_counts[category]
                    if actual_count != expected_count:
                        return EvaluationReason(
                            value=0.0,
                            reason=(
                                f"Count mismatch for {category}: "
                                f"expected {expected_count}, got {actual_count}"
                            ),
                        )
                else:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Category {category} not found in analysis",
                    )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying category counts: {e}")

        return 1.0


class DatasetComparisonTask(FilesystemTask):
    """Task for comparing ScanNet and SUN RGB-D datasets.

    The agent must:
    1. Map ScanNet object categories to SUN RGB-D categories
    2. Calculate object counts for each SUN RGB-D category
    3. Generate analysis.txt with format: category name, count, empty line
    4. Include all 10 SUN RGB-D categories with correct counts
    """

    name = "dataset_comparison"
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

Analyze the codebase to map ScanNet object categories to SUN RGB-D categories and calculate object counts.

### Task Objectives

1. **Primary Goal**: Use SUN RGB-D's 10-category classification system as the target taxonomy
2. **Mapping Requirement**: Map each ScanNet object category (using the "category" field, not "raw_category") to the corresponding SUN RGB-D category
3. **Calculation**: For each SUN RGB-D category, calculate the total count of objects from ScanNet that map to that category (It only counts if the category (not raw category) name are exactly the same (night_stand = nightstand))
4. **Output**: Generate an analysis.txt file in the main directory showing the mapping and counts

### Expected Output

Create a file named `analysis.txt` in the test directory root with the following format:

- Each SUN RGB-D category should be represented as a 2-line block
- Line 1: category name
- Line 2: total count
- Each block should be separated by one empty line

### Success Criteria

The analysis.txt file should contain all 10 SUN RGB-D categories:
chair, table, bed, bookshelf, desk, toilet, dresser, bathtub, sofa, night_stand

With correct counts:
- chair: 4681
- table: 1170
- bed: 370
- bookshelf: 377
- desk: 680
- toilet: 256
- dresser: 213
- bathtub: 144
- sofa: 1
- night_stand: 224"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            AnalysisFileExists(),
            FileLocation(),
            AnalysisFormat(),
            RequiredCategories(),
            CategoryCounts(),
        )

