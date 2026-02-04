"""Utilities for Postgres domain: PgConfig, stream_to_logger, run_pg_restore, download_backup."""

import os
import subprocess
from enum import StrEnum
from functools import partial
from pathlib import Path
from typing import Any

import anyio
from anyio.abc import ByteReceiveStream
from anyio.streams.text import TextReceiveStream
from loguru import logger
from pydantic_settings import SettingsConfigDict

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


class PgConfig(DomainSecrets):
    """PostgreSQL connection parameters."""

    model_config = SettingsConfigDict(env_prefix="PG_")

    image: str = "pgvector/pgvector:0.8.0-pg17-bookworm"
    host: str = "pg"
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
    *,
    log_fn: Any,  # noqa: ANN401
    label: str,
) -> None:
    """Async iterate over a byte stream, decode lines, and log via log_fn."""
    try:
        async for text in TextReceiveStream(reader):
            line = text.rstrip()
            if line:
                log_fn("[%s] %s", label, line)
    except (anyio.ClosedResourceError, anyio.EndOfStream):
        pass


async def run_pg_restore(
    dump_path: str,
    db_name: str,
    pg_config: PgConfig,
    env_extra: dict[str, str] | None = None,
) -> None:
    """Run pg_restore via anyio; stream stdout/stderr to logger; raise on non-zero exit."""
    cmd = [
        "pg_restore",
        "-h",
        pg_config.host,
        "-p",
        str(pg_config.port),
        "-U",
        pg_config.user,
        "-d",
        db_name,
        "-v",
        dump_path,
    ]
    env = {
        **os.environ,
        "PGPASSWORD": pg_config.password,
        **(env_extra or {}),
    }
    async with await anyio.open_process(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    ) as proc:
        if proc.stdout is not None and proc.stderr is not None:
            async with anyio.create_task_group() as tg:
                tg.start_soon(
                    partial(stream_to_logger, log_fn=logger.debug, label="stdout"),
                    proc.stdout,
                )
                tg.start_soon(
                    partial(stream_to_logger, log_fn=logger.debug, label="stderr"),
                    proc.stderr,
                )
        rc = await proc.wait()
    if rc != 0:
        msg = f"pg_restore failed with exit code {rc}"
        raise RuntimeError(msg)


async def download_backup(backup: Backup) -> Path:
    """Download backup from mcpmark storage to cache dir; return path to the file."""
    cache_dir = Path(appdirs.user_cache_dir("mcp_evals", "mcp_evals"))
    cache_dir.mkdir(exist_ok=True, parents=True)
    path = cache_dir / f"{backup.value}.backup"

    if path.is_file():
        return path

    url = f"{BACKUP_BASE_URL}/{backup.value}.backup"
    proxy = os.getenv("DOWNLOAD_PROXY")
    async with httpx.AsyncClient(timeout=10, proxy=proxy) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        with path.open("wb") as f:
            f.write(resp.content)
    return path
