"""FileClassification evaluator for size_classification task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.size_classification.constants import (
    EXPECTED_CLASSIFICATION,
    SYSTEM_FILES,
)

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.size_classification.task import SizeClassificationTask


@dataclass
class FileClassification(Evaluator["SizeClassificationTask", AgentRunResult]):
    """Evaluator that checks files are correctly classified into the right directories."""

    async def evaluate(self, ctx: EvaluatorContext[SizeClassificationTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that files are correctly classified into the right directories."""
        task = ctx.inputs

        for dir_name, expected_files in EXPECTED_CLASSIFICATION.items():
            dir_path = task.work_dir / dir_name

            # Check that all expected files are in the directory
            missing_files = []
            for filename in expected_files:
                file_path = dir_path / filename
                if not file_path.exists():
                    missing_files.append(filename)

            if missing_files:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing files in '{dir_name}': {missing_files}",
                )

            # Check that no unexpected files are in the directory
            try:
                actual_files = [f.name for f in dir_path.iterdir() if f.is_file()]
                unexpected_files = [f for f in actual_files if f not in expected_files and f not in SYSTEM_FILES]

                if unexpected_files:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Unexpected files in '{dir_name}': {unexpected_files}",
                    )
            except (OSError, PermissionError) as e:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Error reading directory '{dir_name}': {e}",
                )

        return 1.0
