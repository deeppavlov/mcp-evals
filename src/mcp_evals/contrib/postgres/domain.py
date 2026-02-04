"""Postgres domain: starts PG via aiodocker, provides no MCP; tasks get pg_config."""

from collections.abc import Sequence
from contextlib import AsyncExitStack
from typing import Any

from aiodocker.exceptions import DockerError
from loguru import logger

from mcp_evals import Domain

from .task import PostgresTask
from .tasks import CreatePaymentIndexTask, DepartmentSummaryViewTask, UpdateEmployeeInfoTask
from .utils import PgConfig

try:
    import aiodocker
    from aiodocker.containers import DockerContainer
except ImportError as err:
    raise ImportError("anyio is required for download_backup; install domain-postgres extra") from err
try:
    import anyio
except ImportError as err:
    raise ImportError("anyio is required for download_backup; install domain-postgres extra") from err


class PostgresDomain(Domain[PgConfig]):
    """Domain that runs a PostgreSQL container (aiodocker); tasks restore backups and expose postgres-mcp."""

    name = "postgres"
    secrets_type = PgConfig

    _container: DockerContainer | None = None
    _docker: aiodocker.Docker | None = None

    def __init__(self) -> None:
        """Init."""
        super().__init__()

    async def setup(self, stack: AsyncExitStack[Any]) -> None:
        """Create and start PostgreSQL container; store pg_config."""
        docker = aiodocker.Docker()
        self._docker = docker
        stack.push_async_callback(docker.close)

        logger.debug("[postgres] Starting PostgreSQL container...")

        if not await _image_loaded(self.secrets.image, client=docker):
            await docker.images.pull(from_image=self.secrets.image)

        logger.debug("[postgres] Starting PostgreSQL container...")
        # TODO verity its a valid config
        config = {
            "Image": self.secrets.image,
            "Cmd": [],
            "Env": [
                f"POSTGRES_PASSWORD={self.secrets.password}",
                f"POSTGRES_USER={self.secrets.user}",
            ],
            "ExposedPorts": {"5432/tcp": {}},
            "HostConfig": {
                "PortBindings": {
                    "5432/tcp": [{"HostPort": str(self.secrets.port)}],
                },
            },
        }
        self._container = await docker.containers.create(config=config)  # type: ignore[arg-type]
        stack.push_async_callback(self._stop_and_remove)

        await self._container.start()

        # Give Postgres a moment to accept connections
        await anyio.sleep(3.0)

        logger.debug("[postgres] PostgreSQL container started")

    async def _stop_and_remove(self) -> None:
        if self._container is None:
            return
        try:
            await self._container.stop()
        except Exception:  # noqa: BLE001
            logger.exception("Error stopping postgres container")
        try:
            await self._container.delete(force=True)
        except Exception:  # noqa: BLE001
            logger.exception("Error removing postgres container")
        self._container = None

    def mcp_servers(self) -> Sequence[Any]:
        """Domain provides no MCP; each task provides postgres-mcp."""
        return []

    def tasks(self) -> Sequence[PostgresTask]:
        """Return postgres tasks (each gets pg_config from domain)."""
        if self._container is None:
            raise RuntimeError("PostgresDomain.setup() must run before tasks()")
        cfg = self.secrets
        return [
            CreatePaymentIndexTask(cfg),
            UpdateEmployeeInfoTask(cfg),
            DepartmentSummaryViewTask(cfg),
        ]


async def _image_loaded(image_name: str, client: aiodocker.Docker) -> bool:
    """Checks if a Docker image exists using inspect and handles the error if not found."""
    try:
        await client.images.inspect(image_name)
        logger.debug(f"Image '{image_name}' found using inspect.")
    except DockerError as e:
        if e.status == 404:  # noqa: PLR2004
            logger.debug(f"Image '{image_name}' not found.")
            return False
        logger.exception("An error occurred")
        return False
    else:
        return True
