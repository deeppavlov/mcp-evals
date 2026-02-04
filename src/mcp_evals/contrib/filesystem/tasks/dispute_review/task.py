"""Dispute Review task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .custom_evaluators import ExpectedEntries, OutputFormat


class DisputeReviewTask(FilesystemTask):
    """Task for reviewing legal document disputes and counting comments.

    The agent must:
    1. Review versions v5, v6, v7 in legal_files/
    2. Identify all clauses that have been commented
    3. Generate dispute_review.txt with format: Clause number:number of comments
    """

    name = "dispute_review"
    goal = """Please use FileSystem tools to finish the following task:

**Overview**

The folder "legal_files/" contains all versions
(Preferred_Stock_Purchase_Agreement_v0.txt -- Preferred_Stock_Purchase_Agreement_v10.txt)
of the Stock Purchase Agreement for a corporate investment project.

There are comments in it, come from four people:
- **Bill Harvey** (Company CEO)
- **Michelle Jackson** (Investor)
- **David Russel** (Company Counsel)
- **Tony Taylor** (Investor Counsel)

Between v1 and v9, these four people make comments on the clauses. The comment format is `[name:content]`, where:
- `name` is the commenter's name
- `content` is the revision note

**Special Note:** If the name is "All parties", it represents a joint comment from all parties,
which counts as one comment but does not count toward any individual's personal comment count.

## Task

Your task is to review these versions and identify all clauses that have been commented
in **v5,6,7 (in folder legal_files/)**. Generate a file named `dispute_review.txt` in the main directory.
In this file, list each commented clause on a separate line and indicate the number of comments
for each clause in the format "Clause number:number of comments".
Clause number should be in the format of X.X."""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FileExists("dispute_review.txt"),
            OutputFormat(),
            ExpectedEntries(),
        )
