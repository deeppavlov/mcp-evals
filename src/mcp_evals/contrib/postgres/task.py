"""Base class for Postgres tasks: restore backup, expose postgres-mcp, provide pg_conn_params."""

import time
from contextlib import AsyncExitStack
from typing import Any

import psycopg
from psycopg import sql
from pydantic import BaseModel, Field
from pydantic_ai.mcp import MCPServerStdio

from mcp_evals.secrets import TaskSecrets
from mcp_evals.task import Task

from .utils import Backup, PgConfig, download_backup, run_pg_restore


class FinishTask(BaseModel):
    """Optional structured output for postgres tasks."""

    answer: str | None = Field(None, description="Optional answer")


class PostgresTask(Task[TaskSecrets, FinishTask]):
    """Base for postgres tasks: download backup, create DB, pg_restore, expose postgres-mcp."""

    output_type = FinishTask

    def __init__(self, pg_config: PgConfig, category_id: Backup) -> None:
        """Init."""
        super().__init__()
        self._pg_config = pg_config
        self._category_id = category_id
        self._database_name: str | None = None

    async def setup(self, stack: AsyncExitStack[Any]) -> None:
        """Download backup, create DB, run pg_restore; register drop DB on teardown."""
        dump_path = await download_backup(self._category_id)
        ts = int(time.time() * 1000)
        db_name = f"mcp_evals_pg_{self._category_id}_{self.name}_{ts}".replace("-", "_")
        self._database_name = db_name

        # Create empty database (connect to 'postgres')
        conninfo = f"{self._pg_config.connection_string}/postgres"
        async with await psycopg.AsyncConnection.connect(
            conninfo=conninfo,
            autocommit=True,
        ) as conn:
            await conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))

        await run_pg_restore(str(dump_path), db_name, self._pg_config)

        async def drop_db() -> None:
            async with await psycopg.AsyncConnection.connect(
                conninfo=conninfo,
                autocommit=True,
            ) as conn:
                await conn.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity \
WHERE datname = %s AND pid <> pg_backend_pid()",
                    (db_name,),
                )
                await conn.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(db_name)))

        stack.push_async_callback(drop_db)

    def mcp_servers(self) -> list[MCPServerStdio]:
        """Return postgres-mcp server with DATABASE_URI for this task's DB."""
        if self._database_name is None:
            msg = "Enter task's context with `async with task` before instantiating mcp tools"
            raise RuntimeError(msg)

        uri = self._pg_config.database_uri(self._database_name)
        return [
            MCPServerStdio(
                "docker",
                [
                    "run",
                    "-i",
                    "--rm",
                    "-e",
                    "DATABASE_URI",
                    "crystaldba/postgres-mcp",
                    "--access-mode=unrestricted",
                ],
                env={"DATABASE_URI": uri},
            )
        ]

    def pg_conn_params(self) -> dict[str, Any]:
        """Connection params for psycopg.AsyncConnection.connect (e.g. for evaluators)."""
        if self._database_name is None:
            raise RuntimeError("Task not set up yet")
        return {
            "host": self._pg_config.host,
            "port": self._pg_config.port,
            "user": self._pg_config.user,
            "password": self._pg_config.password,
            "dbname": self._database_name,
        }
