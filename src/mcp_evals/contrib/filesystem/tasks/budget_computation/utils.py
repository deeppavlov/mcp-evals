"""Budget Computation task for filesystem domain."""


def path_matches_expected(actual_path: str, expected_path: str) -> bool:
    """Check if actual path contains the expected path (allowing for prefixes like './')."""
    normalized_actual = actual_path
    prefix_tuple = ("./", "../")
    while normalized_actual.startswith(prefix_tuple):
        normalized_actual = normalized_actual[2:] if normalized_actual.startswith("./") else normalized_actual[3:]

    return expected_path in normalized_actual or normalized_actual == expected_path
