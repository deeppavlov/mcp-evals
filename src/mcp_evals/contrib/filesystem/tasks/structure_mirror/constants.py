"""Constants for structure_mirror task."""

# Expected directories that should exist
EXPECTED_DIRS = [
    "deeply",
    "deeply/nested",
    "deeply/nested/folder",
    "deeply/nested/folder/structure",
    "empty_folder",
    "folder_lxkHt_0_1_processed",
    "folder_QdTAj_0_2_processed",
    "folder_xtgyi_0_0_processed",
    "mixed_content",
    "mixed_content/images_and_text",
    "project",
    "project/docs",
    "project/docs/archive",
    "project/docs/archive/2023_processed",
    "project/src",
    "project/src/main",
    "project/src/main/resources",
]

# Directories that should have placeholder.txt files
PLACEHOLDER_DIRS = [
    "deeply/nested/folder/structure",
    "empty_folder",
    "folder_lxkHt_0_1_processed",
    "folder_QdTAj_0_2_processed",
    "folder_xtgyi_0_0_processed",
    "mixed_content/images_and_text",
    "project/docs/archive/2023_processed",
    "project/src/main/resources",
]

MIRROR_DIR_NAME = "complex_structure_mirror"
SOURCE_DIR_NAME = "complex_structure"
