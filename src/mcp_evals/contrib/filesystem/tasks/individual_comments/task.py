"""Individual Comments task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import CSVFormat, FileExists
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .constants import EXPECTED_COLUMN_COUNT
from .custom_evaluators import CSVContent, DataAccuracy


class IndividualCommentsTask(FilesystemTask):
    """Task for counting individual comments by person and clause.

    The agent must:
    1. Count comments by Bill Harvey, Michelle Jackson, David Russel, Tony Taylor
    2. Count comments in clauses 1.1, 1.3, 4.6, 4.16, 6.8, 6.16
    3. Focus on versions 5-8
    4. Generate individual_comment.csv with correct format
    """

    name = "individual_comments"
    goal = """Please use FileSystem tools to finish the following task:

**Overview**

The folder "legal_files/" contains all versions (Preferred_Stock_Purchase_Agreement_v0.txt -- \
Preferred_Stock_Purchase_Agreement_v10.txt) of the Stock Purchase Agreement for a corporate investment project.

There are comments in it, come from four people:
- **Bill Harvey** (Company CEO)
- **Michelle Jackson** (Investor)
- **David Russel** (Company Counsel)
- **Tony Taylor** (Investor Counsel)

Between v1 and v9, these four people make comments on the clauses. The comment format is `[name:content]`, where:
- `name` is the commenter's name
- `content` is the revision note

**Special Note:** If the name is "All parties", it represents a joint comment from all parties, which counts as one \
comment but does not count toward any individual's personal comment count.

## Task

Your task is to count the number of comments made by Bill Harvey (Company CEO), Michelle Jackson (Investor), \
David Russel (Company Counsel), and Tony Taylor (Investor Counsel) in clauses 1.1, 1.3, 4.6, 4.16, 6.8, \
and 6.16 **in version 5-8.** Please generate `individual_comment.csv` in the **main directory** where the \
first row contains these clauses (1.1, 1.3, 4.6, 4.16, 6.8, 6.16) and the first column contains the four names \
(Bill Harvey, Michelle Jackson, David Russel, Tony Taylor). Fill in the table with the number of comments for each \
person and each clause. If there are no comments, write 0."""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            FileExists("individual_comment.csv"),
            CSVFormat("individual_comment.csv", expected_columns=EXPECTED_COLUMN_COUNT),
            CSVContent(),
            DataAccuracy(),
        )
