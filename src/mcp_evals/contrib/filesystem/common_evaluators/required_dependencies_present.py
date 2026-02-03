"""Common evaluators shared across filesystem tasks."""

from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.task import FilesystemTask


@dataclass
class RequiredDependenciesPresent(Evaluator[FilesystemTask, AgentRunResult]):
    """Evaluator that checks if required dependencies are present in a requirements.txt file.

    Example:
        RequiredDependenciesPresent("requirements.txt", ["matplotlib", "opencv", "numpy"])
        RequiredDependenciesPresent("requirements.txt", REQUIRED_DEPS)
    """

    file_path: str
    dependencies: list[str]

    async def evaluate(self, ctx: EvaluatorContext[FilesystemTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify that all required dependencies are present in the requirements file.

        The file path is resolved relative to the task's work directory.
        Dependencies are checked case-insensitively.
        """
        task = ctx.inputs
        requirements_file = task.work_dir / Path(self.file_path)

        if not requirements_file.exists():
            return EvaluationReason(
                value=0.0,
                reason=f"File '{self.file_path}' does not exist",
            )

        try:
            content = requirements_file.read_text(encoding="utf-8")

            missing_deps = []
            found_deps = []

            for dep in self.dependencies:
                if dep.lower() in content.lower():
                    found_deps.append(dep)
                else:
                    missing_deps.append(dep)

            if missing_deps:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Missing required dependencies: {missing_deps}",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(
                value=0.0,
                reason=f"Error checking dependencies: {e}",
            )

        return 1.0
