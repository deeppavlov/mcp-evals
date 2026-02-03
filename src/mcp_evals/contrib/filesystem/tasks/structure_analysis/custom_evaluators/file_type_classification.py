"""FileTypeClassification evaluator for structure_analysis task."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.structure_analysis.constants import EXPECTED_PY_COUNT, EXPECTED_TXT_COUNT

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.structure_analysis.task import StructureAnalysisTask


@dataclass
class FileTypeClassification(Evaluator["StructureAnalysisTask", AgentRunResult]):
    """Evaluator that checks file type classification is correct."""

    async def evaluate(self, ctx: EvaluatorContext[StructureAnalysisTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify subtask 3: File Type Classification."""
        task = ctx.inputs
        analysis_file = task.work_dir / "structure_analysis.txt"

        try:
            content = analysis_file.read_text(encoding="utf-8")

            txt_match = re.search(r"txt:\s*(\d+)", content, re.IGNORECASE)
            py_match = re.search(r"py:\s*(\d+)", content, re.IGNORECASE)

            if not txt_match or not py_match:
                return EvaluationReason(
                    value=0.0,
                    reason="Could not extract file type counts from structure_analysis.txt",
                )

            txt_count = int(txt_match.group(1))
            py_count = int(py_match.group(1))

            if txt_count != EXPECTED_TXT_COUNT:
                return EvaluationReason(
                    value=0.0,
                    reason=f"txt count must be {EXPECTED_TXT_COUNT}, found: {txt_count}",
                )

            if py_count != EXPECTED_PY_COUNT:
                return EvaluationReason(
                    value=0.0,
                    reason=f"py count must be {EXPECTED_PY_COUNT}, found: {py_count}",
                )

        except (OSError, UnicodeDecodeError, ValueError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying file type classification: {e}")

        return 1.0
