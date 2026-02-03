"""Budget Computation task for filesystem domain."""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.run import AgentRunResult
from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext, EvaluatorOutput

from mcp_evals.contrib.filesystem.common_evaluators import FileContentStructure
from mcp_evals.contrib.filesystem.task import FilesystemTask
from mcp_evals.contrib.filesystem.utils import Fixture

# Expected expenses based on answer.txt
EXPECTED_EXPENSES = [
    ("Archives/tax_documents_2022.csv", 42000.00),
    ("Archives/tax_documents_2022.csv", 1800.00),
    ("Archives/tax_documents_2022.csv", 950.00),
    ("Documents/Personal/tax_info_2023.csv", 45000.00),
    ("Documents/Personal/tax_info_2023.csv", 2500.00),
    ("Documents/Personal/tax_info_2023.csv", 1200.00),
    ("Documents/budget.csv", 250.00),
    ("Documents/budget.csv", 180.00),
    ("Documents/budget.csv", 120.00),
    ("Downloads/expenses.csv", 45.99),
    ("Downloads/expenses.csv", 99.00),
    ("Downloads/expenses.csv", 234.50),
    ("Downloads/price_comparisons.csv", 879.99),
    ("Downloads/price_comparisons.csv", 289.99),
    ("Downloads/price_comparisons.csv", 74.99),
]

# Expected file paths and their counts
EXPECTED_PATHS = {
    "Archives/tax_documents_2022.csv": 3,
    "Documents/Personal/tax_info_2023.csv": 3,
    "Documents/budget.csv": 3,
    "Downloads/expenses.csv": 3,
    "Downloads/price_comparisons.csv": 3,
}

EXPECTED_TOTAL = 95624.46
EXPECTED_EXPENSE_COUNT = 15
EXPECTED_TOTAL_LINES = 16  # 15 expenses + 1 total


def path_matches_expected(actual_path: str, expected_path: str) -> bool:
    """Check if actual path contains the expected path (allowing for prefixes like './')."""
    normalized_actual = actual_path
    while normalized_actual.startswith("./") or normalized_actual.startswith("../"):
        if normalized_actual.startswith("./"):
            normalized_actual = normalized_actual[2:]
        else:
            normalized_actual = normalized_actual[3:]

    return expected_path in normalized_actual or normalized_actual == expected_path


@dataclass
class TotalBudgetFileExists(Evaluator["BudgetComputationTask", AgentRunResult]):
    """Evaluator that checks total_budget.txt file exists."""

    async def evaluate(self, ctx: EvaluatorContext["BudgetComputationTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the total_budget.txt file exists."""
        task = ctx.inputs
        budget_file = task.work_dir / "total_budget.txt"

        if not budget_file.exists():
            return EvaluationReason(value=0.0, reason="File 'total_budget.txt' not found")

        return 1.0


@dataclass
class FileFormat(Evaluator["BudgetComputationTask", AgentRunResult]):
    """Evaluator that checks total_budget.txt file has proper format."""

    async def evaluate(self, ctx: EvaluatorContext["BudgetComputationTask", AgentRunResult]) -> EvaluatorOutput:  # noqa: PLR0911
        """Verify that the total_budget.txt file has proper format."""
        task = ctx.inputs
        budget_file = task.work_dir / "total_budget.txt"

        try:
            content = budget_file.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            if len(lines) < 2:
                return EvaluationReason(
                    value=0.0,
                    reason="File must contain at least 2 lines (expenses + total)",
                )

            # Check that all lines except the last follow the format file_path;price
            for i, line in enumerate(lines[:-1]):
                if ";" not in line:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Line {i + 1} does not contain ';' separator: {line}",
                    )

                parts = line.split(";")
                if len(parts) != 2:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Line {i + 1} does not have exactly 2 parts: {line}",
                    )

                # Check if second part is a valid number
                try:
                    float(parts[1])
                except ValueError:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Line {i + 1} price is not a valid number: {parts[1]}",
                    )

            # Check if last line is a valid number (total)
            try:
                float(lines[-1])
            except ValueError:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Last line is not a valid number: {lines[-1]}",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error reading or parsing file: {e}")

        return 1.0


@dataclass
class ExpenseEntries(Evaluator["BudgetComputationTask", AgentRunResult]):
    """Evaluator that checks all 15 required expense entries are present."""

    async def evaluate(self, ctx: EvaluatorContext["BudgetComputationTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all 15 required expense entries are present."""
        task = ctx.inputs
        budget_file = task.work_dir / "total_budget.txt"

        try:
            content = budget_file.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            if len(lines) != EXPECTED_TOTAL_LINES:
                return EvaluationReason(
                    value=0.0,
                    reason=(
                        f"Expected {EXPECTED_TOTAL_LINES} lines "
                        f"({EXPECTED_EXPENSE_COUNT} expenses + 1 total), found {len(lines)}"
                    ),
                )

            expense_lines = lines[:-1]

            if len(expense_lines) != EXPECTED_EXPENSE_COUNT:
                return EvaluationReason(
                    value=0.0,
                    reason=(f"Expected {EXPECTED_EXPENSE_COUNT} expense entries, found {len(expense_lines)}"),
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking expense entries: {e}")

        return 1.0


@dataclass
class FilePathsAndCounts(Evaluator["BudgetComputationTask", AgentRunResult]):
    """Evaluator that checks all required file paths are present with correct counts."""

    async def evaluate(self, ctx: EvaluatorContext["BudgetComputationTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all required file paths are present with correct counts."""
        task = ctx.inputs
        budget_file = task.work_dir / "total_budget.txt"

        try:
            content = budget_file.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.split("\n") if line.strip()]
            expense_lines = lines[:-1]

            # Extract file paths from expense lines
            file_paths = []
            for line in expense_lines:
                file_path = line.split(";")[0]
                file_paths.append(file_path)

            # Count occurrences of each path
            path_counts = Counter(file_paths)

            # Check if all expected paths are present with correct counts
            for expected_path, expected_count in EXPECTED_PATHS.items():
                matching_paths = []
                for actual_path in path_counts.keys():
                    if path_matches_expected(actual_path, expected_path):
                        matching_paths.append(actual_path)

                if not matching_paths:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Missing expected file path: {expected_path}",
                    )

                total_count = sum(path_counts[path] for path in matching_paths)
                if total_count != expected_count:
                    msg = f"Path {expected_path} has wrong count: expected {expected_count}, found {total_count}"
                    return EvaluationReason(value=0.0, reason=msg)

            # Check if there are any completely unexpected paths
            all_matching_paths = set()
            for expected_path in EXPECTED_PATHS:
                for actual_path in path_counts:
                    if path_matches_expected(actual_path, expected_path):
                        all_matching_paths.add(actual_path)

            unexpected_paths = set(path_counts) - all_matching_paths
            if unexpected_paths:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Unexpected file paths found: {sorted(unexpected_paths)}",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking file paths: {e}")

        return 1.0


@dataclass
class IndividualPrices(Evaluator["BudgetComputationTask", AgentRunResult]):
    """Evaluator that checks all individual prices match the expected values."""

    async def evaluate(self, ctx: EvaluatorContext["BudgetComputationTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that all individual prices match the expected values."""
        task = ctx.inputs
        budget_file = task.work_dir / "total_budget.txt"

        try:
            content = budget_file.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.split("\n") if line.strip()]
            expense_lines = lines[:-1]

            # Parse actual expenses
            actual_expenses = []
            for line in expense_lines:
                parts = line.split(";")
                file_path = parts[0]
                price = float(parts[1])
                actual_expenses.append((file_path, price))

            # Create counters for expected and actual expenses
            expected_expenses_counter = Counter(EXPECTED_EXPENSES)
            actual_expenses_counter = Counter(actual_expenses)

            # Check if all expected expenses are present with correct counts
            for expected_expense, expected_count in expected_expenses_counter.items():
                expected_path, expected_price = expected_expense

                matching_expenses = []
                for actual_expense in actual_expenses_counter:
                    actual_path, actual_price = actual_expense
                    price_match = abs(actual_price - expected_price) < 0.01
                    path_match = path_matches_expected(actual_path, expected_path)
                    if path_match and price_match:
                        matching_expenses.append(actual_expense)

                if not matching_expenses:
                    return EvaluationReason(
                        value=0.0,
                        reason=f"Missing expected expense: {expected_expense}",
                    )

                total_count = sum(actual_expenses_counter[expense] for expense in matching_expenses)
                if total_count != expected_count:
                    msg = f"Expense {expected_expense} has wrong count: expected {expected_count}, found {total_count}"
                    return EvaluationReason(value=0.0, reason=msg)

            # Check if there are any completely unexpected expenses
            all_matching_expenses = set()
            for expected_expense in expected_expenses_counter.keys():
                expected_path, expected_price = expected_expense
                for actual_expense in actual_expenses_counter.keys():
                    actual_path, actual_price = actual_expense
                    if path_matches_expected(actual_path, expected_path) and abs(actual_price - expected_price) < 0.01:
                        all_matching_expenses.add(actual_expense)

            unexpected_expenses = set(actual_expenses_counter.keys()) - all_matching_expenses
            if unexpected_expenses:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Unexpected expenses found: {sorted(unexpected_expenses)}",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking individual prices: {e}")

        return 1.0


@dataclass
class TotalPrice(Evaluator["BudgetComputationTask", AgentRunResult]):
    """Evaluator that checks the total price is correct."""

    async def evaluate(self, ctx: EvaluatorContext["BudgetComputationTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the total price is correct."""
        task = ctx.inputs
        budget_file = task.work_dir / "total_budget.txt"

        try:
            content = budget_file.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            total_line = lines[-1]
            try:
                actual_total = float(total_line)
            except ValueError:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Last line is not a valid number: {total_line}",
                )

            if abs(actual_total - EXPECTED_TOTAL) > 0.01:
                return EvaluationReason(
                    value=0.0,
                    reason=f"Expected total {EXPECTED_TOTAL}, found {actual_total}",
                )

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error checking total price: {e}")

        return 1.0


@dataclass
class TotalCalculation(Evaluator["BudgetComputationTask", AgentRunResult]):
    """Evaluator that checks the total matches the sum of individual expenses."""

    async def evaluate(self, ctx: EvaluatorContext["BudgetComputationTask", AgentRunResult]) -> EvaluatorOutput:
        """Verify that the total matches the sum of individual expenses."""
        task = ctx.inputs
        budget_file = task.work_dir / "total_budget.txt"

        try:
            content = budget_file.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.split("\n") if line.strip()]
            expense_lines = lines[:-1]

            calculated_total = 0.0
            for line in expense_lines:
                price = float(line.split(";")[1])
                calculated_total += price

            stated_total = float(lines[-1])

            if abs(calculated_total - stated_total) > 0.01:
                msg = f"Total calculation mismatch: calculated {calculated_total:.2f}, stated {stated_total:.2f}"
                return EvaluationReason(value=0.0, reason=msg)

        except (OSError, UnicodeDecodeError) as e:
            return EvaluationReason(value=0.0, reason=f"Error verifying total calculation: {e}")

        return 1.0


class BudgetComputationTask(FilesystemTask):
    """Task for calculating personal life expenses and creating budget summary.

    The agent must:
    1. Locate and analyze all files in the desktop environment
    2. Extract personal life expenses (exclude project/work expenses)
    3. Create total_budget.txt with format file_path;price
    4. Add total sum as the last line
    """

    name = "budget_computation"
    goal = """Please use FileSystem tools to finish the following task:

### Task Description

You need to analyze all the files in the desktop environment to calculate personal life expenses and create a budget summary.

### Task Objectives

1. **Locate and analyze all files** in the desktop environment
2. **Extract personal life expenses** from the files (such as salary, food, living material, tax, expenses on the internet, ...) (exclude expenses in project/work)
3. **Create a file named `total_budget.txt`** in the main directory
4. **Format each expense entry** as `file_path;price` (one per line)
5. **Add total sum** as the last line, rounded to 2 decimal places

### Output Format

The `total_budget.txt` file should contain:

- One expense per line in format: `file_path;price`
- File path should be the relative path from the main directory
- Price should be rounded to 2 decimal places
- Last line should be the total sum
- No additional text or explanations

### Important Notes

- Only include personal life expenses (not in project/work)
- Use the cheapest available price when multiple options exist for one thing
- The total should match the sum of all individual expenses
- Hint: If a file contains 1 item for personal consumption, it means that all the entry in entire file is for personal consumption"""

    def __init__(self, work_dir: Path, fixture: Fixture) -> None:
        """Initialize the task with evaluators."""
        super().__init__(work_dir=work_dir, fixture=fixture)
        self.evaluators = (
            TotalBudgetFileExists(),
            FileFormat(),
            FileContentStructure("total_budget.txt", expected_lines=EXPECTED_TOTAL_LINES),
            ExpenseEntries(),
            FilePathsAndCounts(),
            IndividualPrices(),
            TotalPrice(),
            TotalCalculation(),
        )
