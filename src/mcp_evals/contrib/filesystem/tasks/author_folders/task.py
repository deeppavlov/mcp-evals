"""Author Folders task for filesystem domain."""

from pathlib import Path

from mcp_evals.contrib.filesystem.common_evaluators import DirectoriesExist
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

from .custom_evaluators import (
    Authors2025Organization,
    FrequentAuthorsOrganization,
    NamingConvention,
    OriginalFilesIntact,
)


class AuthorFoldersTask(FilesystemTask):
    """Task for organizing papers by author into author-specific folders.

    The agent must:
    1. Extract author information from all HTML papers
    2. Identify authors with ≥4 papers total (frequent_authors)
    3. Identify authors with ≥3 papers in 2025 (2025_authors)
    4. Create directories and copy papers to respective folders
    """

    name = "author_folders"
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

You are given a directory containing multiple paper files. You have a collection of academic papers in HTML format \
from arXiv. Your task is to analyze these papers, identify authors who have published multiple papers, and organize \
them into author-specific folders based on specified criteria.

### Task Objectives

#### Part 1: Frequent Authors (≥4 papers)
1. **Extract author information** from all HTML papers in the given directory
2. **Identify authors** who appear in 4 or more papers
3. **Create a directory** `frequent_authors`
4. **Create individual folders** within this directory for each frequent author (lowercase names with underscores)
5. **Copy their papers** to their respective folders

#### Part 2: Prolific 2025 Authors (≥3 papers)
1. **Extract publication dates** along with author information
2. **Identify authors** who published 3 or more papers in 2025
3. **Create a directory** `2025_authors` for 2025 authors
4. **Create individual folders** within this directory for each prolific 2025 author (lowercase names with underscores)
5. **Copy their 2025 papers** to their respective folders

### Expected Output

#### Directory Structure:
```
[given_task_folder]/
├── [original HTML files remain untouched]
├── frequent_authors/              # Authors with ≥4 papers total
│   ├── smith_john/
│   │   └── [copied papers]
│   ├── johnson_sarah/
│   │   └── [copied papers]
│   └── ...
└── 2025_authors/                  # Authors with ≥3 papers in 2025
    ├── williams_david/
    │   └── [copied 2025 papers]
    ├── brown_emily/
    │   └── [copied 2025 papers]
    └── ...
```

#### Requirements:
- Author folder names should be **lowercase** with underscores replacing spaces/commas
  (e.g., `smith_john`, `williams_david`)
- Papers should be **copied** (not moved) to preserve originals
- Author extraction should handle various name formats correctly"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            DirectoriesExist(["frequent_authors", "2025_authors"]),
            OriginalFilesIntact(),
            FrequentAuthorsOrganization(),
            Authors2025Organization(),
            NamingConvention(),
        )
