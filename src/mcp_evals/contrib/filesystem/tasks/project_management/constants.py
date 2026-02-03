"""Constants for project_management task."""

# Expected files in each directory
EXPECTED_PYTHON_FILES = [
    "study_notes.py",
    "model.py",
    "data_analysis.py",
    "travel_calculator.py",
    "inventory.py",
    "playlist_manager.py",
]

EXPECTED_CSV_FILES = [
    "learning_progress.csv",
    "weekly_schedule.csv",
    "results_record.csv",
    "september_summary.csv",
    "data.csv",
    "favorite_songs.csv",
    "travel_itinerary.csv",
]

EXPECTED_LEARNING_FILES = [
    "learning_roadmap.md",
    "research_topics.md",
    "experiment_summary.md",
    "exp_record.md",
    "README.md",
    "analysis_report.md",
    "learning_goals.md",
]

EXPECTED_ENTERTAINMENT_FILES = [
    "gaming_schedule.md",
    "entertainment_planner.md",
    "travel_bucket_list.md",
]

EXPECTED_MUSIC_FILES = [
    "music_collection.md",
]

# Required directory structure
REQUIRED_DIRS = [
    "experiments",
    "experiments/ml_projects",
    "experiments/data_analysis",
    "learning",
    "learning/progress_tracking",
    "learning/resources",
    "personal",
    "personal/entertainment",
    "personal/collections",
]

# Expected file counts
EXPECTED_COUNTS = {
    "experiments/ml_projects": 6,
    "experiments/data_analysis": 7,
    "learning/resources": 7,
    "learning/progress_tracking": 0,
    "personal/entertainment": 3,
    "personal/collections": 1,
}
