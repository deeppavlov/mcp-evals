"""CSVFilesInDataAnalysis evaluator for project_management task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.project_management.constants import EXPECTED_CSV_FILES

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.project_management.task import ProjectManagementTask


@dataclass
class CSVFilesInDataAnalysis(Evaluator["ProjectManagementTask", AgentRunResult]):
    """Evaluator that checks all CSV files are moved to experiments/data_analysis."""

    async def evaluate(self, ctx: EvaluatorContext[ProjectManagementTask, AgentRunResult]) -> EvaluatorOutput:
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
