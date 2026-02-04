"""Constants for budget_computation task."""

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

PRICE_TOLERANCE = 0.01

MIN_REQUIRED_ROWS = 2

EXPECTED_PARTS = 2
