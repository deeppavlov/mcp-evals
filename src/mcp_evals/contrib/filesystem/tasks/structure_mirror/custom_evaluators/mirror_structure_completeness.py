"""MirrorStructureCompleteness evaluator for structure_mirror task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.structure_mirror.constants import (
    EXPECTED_DIRS,
    MIRROR_DIR_NAME,
    PLACEHOLDER_DIRS,
)
from mcp_evals.contrib.filesystem.tasks.structure_mirror.task import find_mirror_directory

if TYPE_CHECKING:
    from pathlib import Path

    from mcp_evals.contrib.filesystem.tasks.structure_mirror.task import StructureMirrorTask


@dataclass
class MirrorStructureCompleteness(Evaluator["StructureMirrorTask", AgentRunResult]):
    """Evaluator that checks mirror structure is complete and matches expected structure."""

    def _check_directory_exists(self, mirror_path: Path, expected_dir: str) -> EvaluatorOutput | None:
        """Check that a directory exists and is actually a directory."""
        if not mirror_path.exists():
            return EvaluationReason(
                value=0.0,
                reason=f"Expected directory not found: {expected_dir}",
            )

        if not mirror_path.is_dir():
            return EvaluationReason(
                value=0.0,
                reason=f"Expected directory exists but is not a directory: {expected_dir}",
            )
        return None

    def _check_placeholder_file(
        self, placeholder_file: Path, expected_dir: str, mirror_dir: Path
    ) -> EvaluatorOutput | None:
        """Check placeholder.txt file exists and has correct content."""
        if not placeholder_file.exists():
            return EvaluationReason(
                value=0.0,
                reason=f"placeholder.txt not found in: {expected_dir}",
            )

        if not placeholder_file.is_file():
            return EvaluationReason(
                value=0.0,
                reason=f"placeholder.txt exists but is not a file in: {expected_dir}",
            )

        try:
            content = placeholder_file.read_text(encoding="utf-8").strip()

            if not content:
                return EvaluationReason(
                    value=0.0,
                    reason=f"placeholder.txt is empty in: {expected_dir}",
                )

            rel_mirror = placeholder_file.parent.relative_to(mirror_dir)
            expected_ending = f"{MIRROR_DIR_NAME}/{rel_mirror}"

            if not content.endswith(expected_ending):
                return EvaluationReason(
                    value=0.0,
                    reason=(
                        f"placeholder.txt content incorrect in: {expected_dir}. "
                        f"Expected ending: {expected_ending}, Found: {content}"
                    ),
                )
        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error reading placeholder.txt in {expected_dir}: {e}",
            )
        return None

    def _check_unexpected_directories(self, mirror_dir: Path) -> EvaluatorOutput | None:
        """Check that no unexpected directories exist."""
        try:
            for mirror_subdir in mirror_dir.rglob("*"):
                if mirror_subdir.is_dir():
                    relative_path = mirror_subdir.relative_to(mirror_dir)
                    if str(relative_path) not in EXPECTED_DIRS and str(relative_path) != ".":
                        return EvaluationReason(
                            value=0.0,
                            reason=f"Unexpected directory found: {relative_path}",
                        )
        except (OSError, PermissionError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking directory structure: {e}")
        return None

    async def evaluate(self, ctx: EvaluatorContext[StructureMirrorTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that the mirror structure is complete and matches expected structure."""
        task = ctx.inputs
        mirror_dir = find_mirror_directory(task.work_dir)

        if mirror_dir is None:
            return EvaluationReason(value=0.0, reason=f"Mirror directory '{MIRROR_DIR_NAME}' not found")

        # Check that all expected directories exist
        for expected_dir in EXPECTED_DIRS:
            mirror_path = mirror_dir / expected_dir

            dir_check = self._check_directory_exists(mirror_path, expected_dir)
            if dir_check is not None:
                return dir_check

            if expected_dir in PLACEHOLDER_DIRS:
                placeholder_file = mirror_path / "placeholder.txt"
                placeholder_check = self._check_placeholder_file(placeholder_file, expected_dir, mirror_dir)
                if placeholder_check is not None:
                    return placeholder_check

        # Check that no unexpected directories exist
        unexpected_check = self._check_unexpected_directories(mirror_dir)
        if unexpected_check is not None:
            return unexpected_check

        return 1.0
