"""ContentIntegrity evaluator for duplicates_searching task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.duplicates_searching.constants import EXPECTED_DUPLICATE_GROUPS
from mcp_evals.contrib.filesystem.tasks.duplicates_searching.utils import calculate_file_hash

if TYPE_CHECKING:
    from pathlib import Path

    from mcp_evals.contrib.filesystem.tasks.duplicates_searching.task import DuplicatesSearchingTask


@dataclass
class ContentIntegrity(Evaluator["DuplicatesSearchingTask", AgentRunResult]):
    """Evaluator that checks file content integrity is maintained after moving."""

    def _validate_file_hash(
        self, duplicates_dir: Path, group_name: str, filename: str, first_filename: str, expected_hash: str
    ) -> EvaluatorOutput | None:
        """Validate a file exists and has the expected hash."""
        file_path = duplicates_dir / filename
        if not file_path.exists():
            return EvaluationReason(
                value=0.0,
                reason=f"File in group {group_name} not found: {filename}",
            )

        file_hash = calculate_file_hash(file_path)
        if file_hash is None:
            return EvaluationReason(value=0.0, reason=f"Error calculating hash for {filename}")

        if file_hash != expected_hash:
            return EvaluationReason(
                value=0.0,
                reason=f"Files in group {group_name} have different content: {first_filename} vs {filename}",
            )

        return None

    def _validate_group(self, duplicates_dir: Path, group_name: str, files: list[str]) -> EvaluatorOutput | None:
        """Validate a duplicate group has identical content."""
        if len(files) < 2:  # noqa: PLR2004
            return None

        # Calculate hash of the first file in the group
        first_file = duplicates_dir / files[0]
        if not first_file.exists():
            return EvaluationReason(
                value=0.0,
                reason=f"First file of group {group_name} not found: {files[0]}",
            )

        first_hash = calculate_file_hash(first_file)
        if first_hash is None:
            return EvaluationReason(value=0.0, reason=f"Error calculating hash for {files[0]}")

        # Check that all other files in the group have the same hash
        for filename in files[1:]:
            error = self._validate_file_hash(duplicates_dir, group_name, filename, files[0], first_hash)
            if error is not None:
                return error

        return None

    def _validate_all_groups(self, duplicates_dir: Path) -> EvaluatorOutput | None:
        """Validate all duplicate groups."""
        for group_name, files in EXPECTED_DUPLICATE_GROUPS.items():
            error = self._validate_group(duplicates_dir, group_name, files)
            if error is not None:
                return error
        return None

    async def evaluate(self, ctx: EvaluatorContext[DuplicatesSearchingTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that files in each duplicate group have identical content."""
        task = ctx.inputs

        duplicates_dir = task.work_dir / "duplicates"

        if not duplicates_dir.exists():
            return EvaluationReason(value=0.0, reason="Duplicates directory does not exist")

        error = self._validate_all_groups(duplicates_dir)
        if error is not None:
            return error

        return 1.0
