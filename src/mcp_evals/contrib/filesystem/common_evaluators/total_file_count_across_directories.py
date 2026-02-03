"""Common evaluators shared across filesystem tasks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.task import FilesystemTask

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


@dataclass
class TotalFileCountAcrossDirectories(Evaluator[FilesystemTask, AgentRunResult]):
    """Evaluator that counts files across multiple directories and compares to expected total.

    Supports both flat directory lists and nested structures via a resolver function.

    Example:
        # Flat list of directories
        TotalFileCountAcrossDirectories(
            directories=["small_files", "medium_files", "large_files"],
            expected_total=8,
            system_files=[".DS_Store", "Thumbs.db"]
        )

        # Nested structure with resolver
        TotalFileCountAcrossDirectories(
            directories={"07": {"09": [], "25": []}, "08": {"06": []}},
            expected_total=8,
            directory_resolver=resolve_nested_directory
        )
    """

    directories: list[str] | dict[str, Any]
    expected_total: int
    system_files: list[str] = field(default_factory=lambda: [".DS_Store", "Thumbs.db", ".DS_Store?", "._.DS_Store"])
    directory_resolver: Callable[[Path, Any], Path | None] | None = None

    def _count_files_in_directory(self, dir_path: Path) -> int:
        """Count non-system files in a directory."""
        try:
            files_in_dir = [f for f in dir_path.iterdir() if f.is_file() and f.name not in self.system_files]
            return len(files_in_dir)
        except (OSError, PermissionError):
            return 0

    def _count_nested_directories(self, work_dir: Path, directories: dict[str, Any]) -> int:
        """Count files in nested directory structure using resolver."""
        if self.directory_resolver is None:
            return 0

        total = 0
        for key, value in directories.items():
            resolved_dir = self.directory_resolver(work_dir, key)
            if resolved_dir is None:
                continue

            # If value is a dict, it's a nested structure (e.g., month -> days)
            if isinstance(value, dict):
                for sub_key in value:
                    sub_resolved_dir = self.directory_resolver(resolved_dir, sub_key)
                    if sub_resolved_dir and sub_resolved_dir.exists():
                        total += self._count_files_in_directory(sub_resolved_dir)
            # If value is a list or other, treat resolved_dir as the final directory
            elif resolved_dir.exists():
                total += self._count_files_in_directory(resolved_dir)

        return total

    def _count_flat_directories(self, work_dir: Path, directories: list[str]) -> int:
        """Count files in flat list of directories."""
        total = 0
        for dir_name in directories:
            dir_path = work_dir / dir_name
            if dir_path.exists():
                total += self._count_files_in_directory(dir_path)
        return total

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Count files across directories and compare to expected total.

        If directory_resolver is provided, it's used to resolve nested structures.
        Otherwise, directories is treated as a flat list of directory names.
        """
        task = ctx.inputs

        if self.directory_resolver is not None:
            # Handle nested structure using resolver
            if not isinstance(self.directories, dict):
                return EvaluationReason(
                    value=0.0,
                    reason="directories must be a dict when directory_resolver is provided",
                )
            total_actual = self._count_nested_directories(task.work_dir, self.directories)
        else:
            # Handle flat list of directories
            if not isinstance(self.directories, list):
                return EvaluationReason(
                    value=0.0,
                    reason="directories must be a list when directory_resolver is not provided",
                )
            total_actual = self._count_flat_directories(task.work_dir, self.directories)

        if total_actual != self.expected_total:
            return EvaluationReason(
                value=0.0,
                reason=f"Expected {self.expected_total} files total, found {total_actual}",
            )

        return 1.0
