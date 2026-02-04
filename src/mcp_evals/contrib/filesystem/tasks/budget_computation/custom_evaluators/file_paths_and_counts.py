"""FilePathsAndCounts evaluator for budget_computation task."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.budget_computation.constants import EXPECTED_PATHS
from mcp_evals.contrib.filesystem.tasks.budget_computation.utils import path_matches_expected

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.budget_computation.task import BudgetComputationTask


@dataclass
class FilePathsAndCounts(Evaluator["BudgetComputationTask", AgentRunResult]):
    """Evaluator that checks all required file paths are present with correct counts."""

    async def evaluate(self, ctx: EvaluatorContext[BudgetComputationTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that all required file paths are present with correct counts."""
        task = ctx.inputs
        budget_file = task.work_dir / "total_budget.txt"

        try:
            content = budget_file.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.split("\n") if line.strip()]
            expense_lines = lines[:-1]

            # Extract file paths from expense lines
            file_paths = [line.split(";")[0] for line in expense_lines]

            # Count occurrences of each path
            path_counts = Counter(file_paths)

            # Check if all expected paths are present with correct counts
            for expected_path, expected_count in EXPECTED_PATHS.items():
                matching_paths = [
                    actual_path for actual_path in path_counts if path_matches_expected(actual_path, expected_path)
                ]

                if not matching_paths:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Missing expected file path: {expected_path}",
                    )

                total_count = sum(path_counts[path] for path in matching_paths)
                if total_count != expected_count:
                    msg = f"Path {expected_path} has wrong count: expected {expected_count}, found {total_count}"
                    return EvaluationReason(value=0.0, reason=msg)

            # Check if there are any completely unexpected paths
            all_matching_paths = set()
            for expected_path in EXPECTED_PATHS:
                for actual_path in path_counts:
                    if path_matches_expected(actual_path, expected_path):
                        all_matching_paths.add(actual_path)

            unexpected_paths = set(path_counts) - all_matching_paths
            if unexpected_paths:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Unexpected file paths found: {sorted(unexpected_paths)}",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking file paths: {e}")

        return 1.0
