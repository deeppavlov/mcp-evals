"""Utilities for downloading and managing filesystem test fixtures."""

import shutil
import zipfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiofiles.tempfile
import httpx
from appdirs import user_cache_dir

# URL mapping for different test environment categories
FIXTURE_URL_MAPPING = {
    "desktop": "https://storage.mcpmark.ai/filesystem/desktop.zip",
    "file_context": "https://storage.mcpmark.ai/filesystem/file_context.zip",
    "file_property": "https://storage.mcpmark.ai/filesystem/file_property.zip",
    "folder_structure": "https://storage.mcpmark.ai/filesystem/folder_structure.zip",
    "papers": "https://storage.mcpmark.ai/filesystem/papers.zip",
    "student_database": "https://storage.mcpmark.ai/filesystem/student_database.zip",
    "threestudio": "https://storage.mcpmark.ai/filesystem/threestudio.zip",
    "votenet": "https://storage.mcpmark.ai/filesystem/votenet.zip",
    "legal_document": "https://storage.mcpmark.ai/filesystem/legal_document.zip",
    "desktop_template": "https://storage.mcpmark.ai/filesystem/desktop_template.zip",
}


async def download_fixture(category: str) -> Path:
    """Download and cache a filesystem test fixture.

    Downloads the fixture from storage.mcpmark.ai if not already cached.
    Caches fixtures in user cache directory for reuse.

    Args:
        category: Fixture category (e.g., 'desktop', 'file_context')

    Returns:
        Path to the extracted fixture directory

    Raises:
        ValueError: If category is not supported
        RuntimeError: If download or extraction fails
    """
    if category not in FIXTURE_URL_MAPPING:
        msg = f"Unknown category: {category}. Supported: {', '.join(FIXTURE_URL_MAPPING.keys())}"
        raise ValueError(msg)

    cache_dir = Path(user_cache_dir("mcp-evals", "mcp-evals")) / "fixtures"
    fixture_path = cache_dir / category

    # Return cached fixture if it exists
    if fixture_path.exists() and fixture_path.is_dir():
        return fixture_path

    # Download fixture
    url = FIXTURE_URL_MAPPING[category]
    zip_path = cache_dir / f"{category}.zip"

    # Ensure cache directory exists
    cache_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Download using httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            zip_path.write_bytes(response.content)

        # Extract ZIP file
        with zipfile.ZipFile(zip_path) as zip_file:
            zip_file.extractall(cache_dir)

        # Clean up macOS metadata if present
        macosx_path = cache_dir / "__MACOSX"
        if macosx_path.exists():
            shutil.rmtree(macosx_path)

        # Clean up ZIP file
        zip_path.unlink(missing_ok=True)

    except httpx.HTTPError as e:
        msg = f"Failed to download fixture from {url}: {e}"
        raise RuntimeError(msg) from e
    except zipfile.BadZipFile as e:
        msg = f"Invalid ZIP file for category {category}: {e}"
        raise RuntimeError(msg) from e
    except Exception as e:
        msg = f"Failed to download or extract fixture for category {category}: {e}"
        raise RuntimeError(msg) from e

    # Verify extraction
    if not fixture_path.exists():
        msg = f"Extracted directory not found: {fixture_path}"
        raise RuntimeError(msg)

    return fixture_path


@asynccontextmanager
async def create_isolated_workspace(fixture_path: Path) -> AsyncIterator[Path]:
    """Create isolated workspace by copying fixture to temp directory.

    Returns an async context manager that tasks enter into their AsyncExitStack.
    The temp directory is automatically cleaned up when the context exits.

    Args:
        fixture_path: Path to the fixture directory to copy

    Yields:
        Path to the isolated workspace directory
    """
    async with aiofiles.tempfile.TemporaryDirectory() as temp_dir:
        work_dir = Path(temp_dir) / "workspace"
        shutil.copytree(fixture_path, work_dir)
        yield work_dir
