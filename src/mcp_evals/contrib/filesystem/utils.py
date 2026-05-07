"""Utilities for downloading and managing filesystem test fixtures."""

import os
import shutil
import zipfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from enum import StrEnum
from pathlib import Path

import anyio
from dotenv import load_dotenv
from loguru import logger

try:
    import aiofiles
    import aiofiles.tempfile
except ImportError as e:
    msg = (
        "aiofiles is required for filesystem tasks. "
        "Install with: pip install 'pydantic-ai-mcp-evals[domain-filesystem]'"
    )
    raise ImportError(msg) from e

try:
    import httpx
except ImportError as e:
    msg = "httpx is required for filesystem tasks. Install with: pip install 'pydantic-ai-mcp-evals[domain-filesystem]'"
    raise ImportError(msg) from e

try:
    from appdirs import user_cache_dir  # type: ignore[import-untyped]
except ImportError as e:
    msg = (
        "appdirs is required for filesystem tasks. Install with: pip install 'pydantic-ai-mcp-evals[domain-filesystem]'"
    )
    raise ImportError(msg) from e

try:
    from tqdm import tqdm
except ImportError as e:
    msg = "tqdm is required for filesystem tasks. Install with: pip install 'pydantic-ai-mcp-evals[domain-filesystem]'"
    raise ImportError(msg) from e


class Fixture(StrEnum):
    """Enumeration of available filesystem test fixture categories."""

    # fixtures marked with '!' consume a lot of tokens due to huge text files in them
    DESKTOP = "desktop"
    FILE_CONTEXT = "file_context"
    FILE_PROPERTY = "file_property"
    FOLDER_STRUCTURE = "folder_structure"  # !
    PAPERS = "papers"  # !
    STUDENT_DATABASE = "student_database"  # !
    THREESTUDIO = "threestudio"  # !
    VOTENET = "votenet"
    LEGAL_DOCUMENT = "legal_document"  # !
    DESKTOP_TEMPLATE = "desktop_template"


# URL mapping for different test environment categories
FIXTURE_URL_MAPPING: dict[Fixture, str] = {
    Fixture.DESKTOP: "https://storage.mcpmark.ai/filesystem/desktop.zip",
    Fixture.FILE_CONTEXT: "https://storage.mcpmark.ai/filesystem/file_context.zip",
    Fixture.FILE_PROPERTY: "https://storage.mcpmark.ai/filesystem/file_property.zip",
    Fixture.FOLDER_STRUCTURE: "https://storage.mcpmark.ai/filesystem/folder_structure.zip",
    Fixture.PAPERS: "https://storage.mcpmark.ai/filesystem/papers.zip",
    Fixture.STUDENT_DATABASE: "https://storage.mcpmark.ai/filesystem/student_database.zip",
    Fixture.THREESTUDIO: "https://storage.mcpmark.ai/filesystem/threestudio.zip",
    Fixture.VOTENET: "https://storage.mcpmark.ai/filesystem/votenet.zip",
    Fixture.LEGAL_DOCUMENT: "https://storage.mcpmark.ai/filesystem/legal_document.zip",
    Fixture.DESKTOP_TEMPLATE: "https://storage.mcpmark.ai/filesystem/desktop_template.zip",
}

load_dotenv()

_fixture_locks: dict[Fixture, anyio.Lock] = {}


def _fixture_lock(category: Fixture) -> anyio.Lock:
    lock = _fixture_locks.get(category)
    if lock is None:
        lock = anyio.Lock()
        _fixture_locks[category] = lock
    return lock


async def download_fixture(category: Fixture) -> Path:
    """Download and cache a filesystem test fixture.

    Downloads the fixture from storage.mcpmark.ai if not already cached.
    Caches fixtures in user cache directory for reuse.

    Args:
        category: Fixture category enum value

    Returns:
        Path to the extracted fixture directory

    Raises:
        ValueError: If category is not supported
        RuntimeError: If download or extraction fails

    Note: use `DOWNLOAD_PROXY` env var to load fixtures with proxy.
    """
    if category not in FIXTURE_URL_MAPPING:
        supported = ", ".join(f.value for f in FIXTURE_URL_MAPPING)
        msg = f"Unknown category: {category}. Supported: {supported}"
        logger.error(msg)
        raise ValueError(msg)

    cache_dir = Path(user_cache_dir("pydantic-ai-mcp-evals", "pydantic-ai-mcp-evals")) / "fixtures"
    fixture_path = cache_dir / category

    async with _fixture_lock(category):
        # Return cached fixture if it exists
        if fixture_path.exists() and fixture_path.is_dir():
            logger.debug(f"Using cached fixture '{category.value}'")
            return fixture_path

        # Download fixture
        logger.debug(f"Downloading fixture '{category.value}'")
        url = FIXTURE_URL_MAPPING[category]
        zip_path = cache_dir / f"{category}.zip"

        # Ensure cache directory exists
        cache_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Download using httpx with streaming
            timeout = httpx.Timeout(connect=5.0, read=5.0, write=10.0, pool=5.0)
            proxy_url = os.getenv("DOWNLOAD_PROXY")
            async with (
                httpx.AsyncClient(timeout=timeout, proxy=proxy_url) as client,
                client.stream("GET", url, follow_redirects=True) as response,
            ):
                response.raise_for_status()
                total_size = int(response.headers.get("content-length", 0)) or None
                async with aiofiles.open(zip_path, "wb") as f:
                    with tqdm(
                        total=total_size,
                        unit="B",
                        unit_scale=True,
                        unit_divisor=1024,
                        desc=f"Downloading {category}",
                    ) as pbar:
                        async for chunk in response.aiter_bytes():
                            await f.write(chunk)
                            pbar.update(len(chunk))

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
async def prepare_workspace(fixture_path: Path, work_dir: Path) -> AsyncIterator[None]:
    """Prepare workspace by copying fixture contents directly to root_dir.

    Returns an async context manager that tasks enter into their AsyncExitStack.
    All contents of root_dir are automatically cleaned up when the context exits.

    Args:
        fixture_path: Path to the fixture directory to copy
        work_dir: Path to the root directory which MCP has access to

    Yields:
        None
    """
    # Ensure root_dir exists
    work_dir.mkdir(parents=True, exist_ok=True)

    # Copy fixture contents directly to work_dir
    try:
        for item in fixture_path.iterdir():
            src_path = fixture_path / item.name
            dst_path = work_dir / item.name
            if src_path.is_dir():
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
            else:
                shutil.copy2(src_path, dst_path)
    except Exception as e:
        msg = "Failed to copy fixture contents to work_dir"
        logger.exception(msg)
        raise RuntimeError(msg) from e

    try:
        yield
    finally:
        # Clean up all contents of work_dir on exit
        try:
            if not work_dir.exists():
                logger.warning("Abnormal termination: workspace directory is already removed: {}", work_dir)
            else:
                for item in work_dir.iterdir():
                    item_path = work_dir / item.name
                    if item_path.is_dir():
                        shutil.rmtree(item_path)
                    else:
                        item_path.unlink()
        except (OSError, PermissionError) as e:
            msg = "Error cleaning work_dir on teardown"
            logger.exception(msg)
            raise RuntimeError(msg) from e
