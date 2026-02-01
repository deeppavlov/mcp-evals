"""Base classes for domain and task secrets management."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class DomainSecrets(BaseSettings):
    """Base class for domain-specific secrets.

    Subclass to declare required environment variables:

    ```python
        class SlackSecrets(DomainSecrets):
            slack_bot_token: str   # Required: SLACK_BOT_TOKEN env var
            slack_team_id: str     # Required: SLACK_TEAM_ID env var
    ```

    Then reference in Domain:

    ```python
        class SlackDomain(Domain):
            secrets_type = SlackSecrets

            def mcp_servers(self):
                return [MCPServerStdio(
                    "uvx", "mcp-server-slack",
                    env={"SLACK_BOT_TOKEN": self.secrets.slack_bot_token},
                )]
    ```
    """

    model_config = SettingsConfigDict(extra="ignore", env_file=".env")


class TaskSecrets(BaseSettings):
    """Base class for task-specific secrets.

    Subclass to declare required environment variables:

    ```python
        class MySecrets(TaskSecrets):
            api_key: str           # Required: API_KEY env var
            timeout: int = 30      # Optional with default
    ```

    Then reference in Task:

    ```python
        class MyTask(Task):
            secrets_type = MySecrets

            async def setup(self):
                print(self.secrets.api_key)  # Type-safe access
    ```
    """

    model_config = SettingsConfigDict(extra="ignore", env_file=".env")
