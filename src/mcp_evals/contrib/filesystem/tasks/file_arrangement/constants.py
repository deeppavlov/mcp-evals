"""Constants for file_arrangement task."""

# Required folders
REQUIRED_FOLDERS = ["work", "life", "archives", "temp", "others"]

# Required files in each folder
REQUIRED_FILE_MAPPING = {
    "work": [
        "client_list.csv",
        "timesheet.csv",
        "experiment_results.txt",
        "budget_tracker.csv",
        "expenses.csv",
    ],
    "life": [
        "contacts.csv",
        "budget.csv",
        "fitness_log.csv",
        "price_comparisons.csv",
        "book_list.txt",
        "bookmark_export.txt",
        "emergency_contacts.txt",
    ],
    "archives": [
        "backup_contacts.csv",
        "tax_documents_2022.csv",
        "correspondence_2023.txt",
        "tax_info_2023.csv",
    ],
    "temp": [
        "test_data.csv",
        "draft_letter.txt",
    ],
}

# All required files (for duplicate checking)
ALL_REQUIRED_FILES = [
    "client_list.csv",
    "timesheet.csv",
    "experiment_results.txt",
    "budget_tracker.csv",
    "contacts.csv",
    "budget.csv",
    "expenses.csv",
    "fitness_log.csv",
    "price_comparisons.csv",
    "book_list.txt",
    "bookmark_export.txt",
    "emergency_contacts.txt",
    "backup_contacts.csv",
    "tax_documents_2022.csv",
    "correspondence_2023.txt",
    "tax_info_2023.csv",
    "test_data.csv",
    "draft_letter.txt",
]
