"""Utilities for Postgres domain: PgConfig, stream_to_logger, run_pg_restore, download_backup."""

import os
import subprocess
from enum import StrEnum
from pathlib import Path
from typing import IO, Any, cast

import aiofiles
import anyio
from anyio.abc import ByteReceiveStream
from anyio.streams.text import TextReceiveStream
from loguru import logger
from pydantic_settings import SettingsConfigDict
from tqdm import tqdm

from mcp_evals.secrets import DomainSecrets

try:
    import appdirs  # type: ignore[import-untyped]
except ImportError as err:
    raise ImportError("appdirs is required for download_backup; install domain-postgres extra") from err
try:
    import httpx
except ImportError as err:
    raise ImportError("httpx is required for download_backup; install domain-postgres extra") from err


class Backup(StrEnum):
    """Postgres backups for different tasks."""

    DVD = "dvdrental"
    CHI = "chinook"
    EMPL = "employees"
    SPORTS = "sports"
    LEGO = "lego"


BACKUP_BASE_URL = "https://storage.mcpmark.ai/postgres"

_backup_locks: dict[Backup, anyio.Lock] = {}


def _backup_lock(backup: Backup) -> anyio.Lock:
    lock = _backup_locks.get(backup)
    if lock is None:
        lock = anyio.Lock()
        _backup_locks[backup] = lock
    return lock


class PgConfig(DomainSecrets):
    """PostgreSQL connection parameters."""

    model_config = SettingsConfigDict(env_prefix="PG_")

    image: str = "pgvector/pgvector:0.8.0-pg17-bookworm"
    container: str = "mcp-pg"
    host: str = "localhost"
    port: int = 7432
    user: str = "pg"
    password: str = "pg"  # noqa: S105

    @property
    def connection_string(self) -> str:
        """Connection string without database name (for connecting to 'postgres' to create DB)."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}"

    def database_uri(self, dbname: str) -> str:
        """Full URI including database name (for MCP server and psycopg)."""
        return f"{self.connection_string}/{dbname}"


async def stream_to_logger(
    reader: ByteReceiveStream,
) -> None:
    """Async iterate over a byte stream, decode lines and log."""
    try:
        async for text in TextReceiveStream(reader):
            line = text.rstrip()
            if line:
                logger.debug(line)
    except (anyio.ClosedResourceError, anyio.EndOfStream):
        pass
    except Exception as e:
        msg = "Stream failed"
        logger.exception(msg)
        raise RuntimeError(msg) from e


async def run_pg_restore(
    dump_path: Path,
    db_name: str,
    pg_config: PgConfig,
    container_name: str,
    env_extra: dict[str, str] | None = None,
) -> None:
    """Run pg_restore inside the Postgres container via docker exec -i; stream backup file on stdin.

    The backup file on the host is piped into the container's pg_restore stdin so the
    container does not need the file mounted. Streams stdout/stderr to the logger; raises
    on non-zero exit.
    """
    cmd = [
        "docker",
        "exec",
        "-i",
        container_name,
        "pg_restore",
        "--no-owner",
        "--no-acl",
        "-U",
        pg_config.user,
        "-d",
        db_name,
        "-v",
    ]
    env = {**os.environ, **(env_extra or {})}
    async with (
        aiofiles.open(dump_path, "rb") as backup_file,
        await anyio.open_process(
            cmd,
            stdin=cast("IO[Any]", backup_file),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        ) as proc,
    ):
        if proc.stdout is not None and proc.stderr is not None:
            async with anyio.create_task_group() as tg:
                tg.start_soon(
                    stream_to_logger,
                    proc.stdout,
                )
                # unfortunately, pg_restore puts all outputs to stderr
                tg.start_soon(
                    stream_to_logger,
                    proc.stderr,
                )
        rc = await proc.wait()
    if rc != 0:
        msg = f"pg_restore failed with exit code {rc}"
        raise RuntimeError(msg)


async def download_backup(backup: Backup) -> Path:
    """Download backup from mcpmark storage to cache dir; return path to the file."""
    cache_dir = anyio.Path(appdirs.user_cache_dir("mcp_evals", "mcp_evals"))
    await cache_dir.mkdir(exist_ok=True, parents=True)
    path = cache_dir / f"{backup.value}.backup"

    async with _backup_lock(backup):
        if await path.is_file():
            return Path(path)

        url = f"{BACKUP_BASE_URL}/{backup.value}.backup"
        logger.debug(f"Loading from {url}...")
        timeout = httpx.Timeout(connect=5.0, read=5.0, write=10.0, pool=5.0)
        proxy_url = os.getenv("DOWNLOAD_PROXY")
        async with (
            httpx.AsyncClient(timeout=timeout, proxy=proxy_url) as client,
            client.stream("GET", url, follow_redirects=True) as response,
        ):
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0)) or None
            async with aiofiles.open(path, "wb") as f:
                with tqdm(
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=f"Downloading {backup.value}",
                ) as pbar:
                    async for chunk in response.aiter_bytes():
                        await f.write(chunk)
                        pbar.update(len(chunk))
        return Path(path)
