"""DepthAnalysis evaluator for structure_analysis task."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.structure_analysis.constants import EXPECTED_DEPTH

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.structure_analysis.task import StructureAnalysisTask


@dataclass
class DepthAnalysis(Evaluator["StructureAnalysisTask", AgentRunResult]):
    """Evaluator that checks depth analysis is correct."""

    def _extract_depth(self, content: str) -> tuple[int | None, EvaluatorOutput | None]:
        """Extract depth from content."""
        depth_match = re.search(r"depth:\s*(\d+)", content, re.IGNORECASE)

        if not depth_match:
            return None, EvaluationReason(
                value=0.0,
                reason="Could not extract depth from structure_analysis.txt",
            )

        depth = int(depth_match.group(1))

        if depth != EXPECTED_DEPTH:
            return None, EvaluationReason(
                value=0.0,
                reason=f"Depth must be {EXPECTED_DEPTH}, found: {depth}",
            )

        return depth, None

    def _extract_and_validate_path(
        self, content: str, depth: int, task: StructureAnalysisTask
    ) -> tuple[str | None, EvaluatorOutput | None]:
        """Extract path and validate it."""
        lines = content.split("\n")
        path_line = None
        for i, line in enumerate(lines):
            if line.strip() == f"depth: {depth}" and i + 1 < len(lines):
                path_line = lines[i + 1].strip()
                break

        if not path_line:
            return None, EvaluationReason(
                value=0.0,
                reason="Could not find path line after depth specification",
            )

        # Verify that the path depth matches the declared depth
        path_parts = path_line.split("/")
        actual_depth = len(path_parts)

        if actual_depth != depth:
            msg = f"Path depth mismatch: declared depth is {depth}, but path has {actual_depth} levels"
            return None, EvaluationReason(value=0.0, reason=msg)

        # Verify that this path exists in the test environment
        expected_path = task.work_dir / path_line
        if not expected_path.exists():
            return None, EvaluationReason(value=0.0, reason=f"Path does not exist: {path_line}")

        if not expected_path.is_dir():
            return None, EvaluationReason(
                value=0.0,
                reason=f"Path exists but is not a directory: {path_line}",
            )

        return path_line, None

    async def evaluate(self, ctx: EvaluatorContext[StructureAnalysisTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify subtask 2: Depth Analysis."""
        task = ctx.inputs
        analysis_file = task.work_dir / "structure_analysis.txt"

        try:
            content = analysis_file.read_text(encoding="utf-8")

            depth, error = self._extract_depth(content)
            if error is not None:
                return error
            if depth is None:
                return EvaluationReason(value=0.0, reason="Could not extract depth")

            _, error = self._extract_and_validate_path(content, depth, task)
            if error is not None:
                return error

        except (OSError, UnicodeDecodeError, ValueError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying depth analysis: {e}")

        return 1.0
