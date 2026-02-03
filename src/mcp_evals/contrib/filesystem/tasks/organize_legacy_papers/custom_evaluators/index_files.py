"""Evaluator that checks INDEX.md files exist and have correct format."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.tasks.organize_legacy_papers.constants import EXPECTED_YEARS

if TYPE_CHECKING:
    from mcp_evals.contrib.filesystem.tasks.organize_legacy_papers.task import OrganizeLegacyPapersTask


@dataclass
class IndexFiles(Evaluator["OrganizeLegacyPapersTask", AgentRunResult]):
    """Evaluator that checks INDEX.md files exist and have correct format."""

    async def evaluate(self, ctx: EvaluatorContext[OrganizeLegacyPapersTask, AgentRunResult]) -> EvaluatorOutput:
        """Verify INDEX.md files exist and have correct format."""
        task = ctx.inputs
        organized_dir = task.work_dir / "organized"

        for year in EXPECTED_YEARS:
            index_file = organized_dir / year / "INDEX.md"

            if not index_file.exists():
                return EvaluationReason(value=0.0, reason=f"INDEX.md missing in {year}/")

            try:
                content = index_file.read_text(encoding="utf-8")

                if "ArXiv ID" not in content or "Authors" not in content or "Local Path" not in content:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"INDEX.md in {year}/ missing required columns",
                    )

                year_dir = organized_dir / year
                html_files = list(year_dir.glob("*.html"))
                for html_file in html_files:
                    arxiv_id = html_file.stem
                    if arxiv_id not in content:
                        return EvaluationReason(
                            value=0.0,
                            reason=f"INDEX.md in {year}/ missing paper {arxiv_id}",
                        )
            except (OSError, UnicodeDecodeError) as e:
                return EvaluationReason(value=0.0, reason=f"Error reading INDEX.md in {year}/: {e}")

        return 1.0
