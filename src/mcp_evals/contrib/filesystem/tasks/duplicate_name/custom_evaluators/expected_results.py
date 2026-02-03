"""ExpectedResults evaluator for duplicate_name task."""

from dataclasses import dataclass

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.duplicate_name.constants import (
    EXPECTED_DUPLICATE_COUNT,
    EXPECTED_DUPLICATES,
)
from mcp_evals.contrib.filesystem.tasks.duplicate_name.utils import parse_namesake_file


@dataclass
class ExpectedResults(Evaluator["DuplicateNameTask", AgentRunResult]):
    """Evaluator that checks results match expected answer.md content exactly."""

    def _validate_name_presence(self, namesakes: dict[str, dict[str, int | list[str]]]) -> EvaluatorOutput | None:
        """Validate that all expected names are present and no unexpected names exist."""
        for expected_name in EXPECTED_DUPLICATES:
            if expected_name not in namesakes:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing expected duplicate name: '{expected_name}'",
                )

        for name in namesakes:
            if name not in EXPECTED_DUPLICATES:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Unexpected duplicate name found: '{name}' (not in expected list)",
                )

        return None

    def _validate_name_data(self, name: str, data: dict[str, int | list[str]]) -> EvaluatorOutput | None:
        """Validate data for a single name."""
        expected_ids = set(EXPECTED_DUPLICATES[name])
        ids = data["ids"]
        if not isinstance(ids, list):
            return EvaluationReason(
                value=0.0,
                reason=f"Invalid ids type for '{name}': expected list, got {type(ids).__name__}",
            )
        stated_ids = set(ids)

        if expected_ids != stated_ids:
            return EvaluationReason(
                value=0.0,
                reason=(f"ID mismatch for '{name}'. Expected: {sorted(expected_ids)}, Stated: {sorted(stated_ids)}"),
            )

        if data["count"] != 2:  # noqa: PLR2004
            return EvaluationReason(
                value=0.0,
                reason=f"Count mismatch for '{name}': expected 2, got {data['count']}",
            )

        return None

    def _validate_namesakes(self, namesakes: dict[str, dict[str, int | list[str]]]) -> EvaluatorOutput | None:
        """Validate namesakes against expected data."""
        if len(namesakes) != EXPECTED_DUPLICATE_COUNT:
            reason_msg = f"Expected exactly {EXPECTED_DUPLICATE_COUNT} duplicate names, but found {len(namesakes)}"
            return EvaluationReason(value=0.0, reason=reason_msg)

        error = self._validate_name_presence(namesakes)
        if error is not None:
            return error

        for name, data in namesakes.items():
            error = self._validate_name_data(name, data)
            if error is not None:
                return error

        return None

    async def evaluate(self, ctx: EvaluatorContext["DuplicateNameTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the results match the expected answer.md content exactly."""
        task = ctx.inputs

        namesakes = parse_namesake_file(task.work_dir)

        if not namesakes:
            return EvaluationReason(value=0.0, reason="Failed to parse namesake file")

        error = self._validate_namesakes(namesakes)
        if error is not None:
            return error

        return 1.0

