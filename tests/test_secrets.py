"""Tests for DomainSecrets and TaskSecrets classes."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from pydantic import ValidationError

from mcp_evals.secrets import DomainSecrets, TaskSecrets


class TestDomainSecrets:
    """Tests for DomainSecrets base class."""

    def test_loads_from_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that DomainSecrets loads from environment variables."""
        monkeypatch.setenv("TEST_TOKEN", "secret123")
        monkeypatch.setenv("TEST_ID", "id456")

        class MyDomainSecrets(DomainSecrets):
            test_token: str
            test_id: str

        secrets = MyDomainSecrets()
        assert secrets.test_token == "secret123"
        assert secrets.test_id == "id456"

    def test_ignores_extra_fields(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that DomainSecrets ignores extra environment variables."""
        monkeypatch.setenv("REQUIRED_FIELD", "value")
        monkeypatch.setenv("EXTRA_FIELD", "should_be_ignored")

        class MyDomainSecrets(DomainSecrets):
            required_field: str

        secrets = MyDomainSecrets()
        assert secrets.required_field == "value"
        # Extra field should not cause an error

    def test_loads_from_env_file(self) -> None:
        """Test that DomainSecrets loads from .env file."""
        with TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("TEST_TOKEN=from_file\nTEST_ID=from_file_id\n")

            class MyDomainSecrets(DomainSecrets):
                test_token: str
                test_id: str

            # Change to the temp directory so .env is found
            original_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                secrets = MyDomainSecrets()
                assert secrets.test_token == "from_file"
                assert secrets.test_id == "from_file_id"
            finally:
                os.chdir(original_cwd)

    def test_custom_subclass_works(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that custom DomainSecrets subclasses work correctly."""
        monkeypatch.setenv("API_KEY", "key123")
        monkeypatch.setenv("API_URL", "https://api.example.com")

        class APISecrets(DomainSecrets):
            api_key: str
            api_url: str

        secrets = APISecrets()
        assert secrets.api_key == "key123"
        assert secrets.api_url == "https://api.example.com"

    def test_missing_required_field_raises_error(self) -> None:
        """Test that missing required fields raise ValidationError."""

        class MyDomainSecrets(DomainSecrets):
            required_field: str

        with pytest.raises(ValidationError):
            MyDomainSecrets()

    def test_optional_field_with_default(self) -> None:
        """Test that optional fields with defaults work."""

        class MyDomainSecrets(DomainSecrets):
            required_field: str = "default_value"

        secrets = MyDomainSecrets()
        assert secrets.required_field == "default_value"


class TestTaskSecrets:
    """Tests for TaskSecrets base class."""

    def test_loads_from_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that TaskSecrets loads from environment variables."""
        monkeypatch.setenv("TASK_TOKEN", "task_secret")
        monkeypatch.setenv("TASK_TIMEOUT", "30")

        class MyTaskSecrets(TaskSecrets):
            task_token: str
            task_timeout: int

        secrets = MyTaskSecrets()
        assert secrets.task_token == "task_secret"
        assert secrets.task_timeout == 30

    def test_ignores_extra_fields(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that TaskSecrets ignores extra environment variables."""
        monkeypatch.setenv("REQUIRED_FIELD", "value")
        monkeypatch.setenv("EXTRA_FIELD", "should_be_ignored")

        class MyTaskSecrets(TaskSecrets):
            required_field: str

        secrets = MyTaskSecrets()
        assert secrets.required_field == "value"
        # Extra field should not cause an error

    def test_loads_from_env_file(self) -> None:
        """Test that TaskSecrets loads from .env file."""
        with TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("TASK_TOKEN=from_file\nTASK_TIMEOUT=60\n")

            class MyTaskSecrets(TaskSecrets):
                task_token: str
                task_timeout: int

            # Change to the temp directory so .env is found
            original_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                secrets = MyTaskSecrets()
                assert secrets.task_token == "from_file"
                assert secrets.task_timeout == 60
            finally:
                os.chdir(original_cwd)

    def test_custom_subclass_works(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that custom TaskSecrets subclasses work correctly."""
        monkeypatch.setenv("GITHUB_TOKEN", "gh_token")
        monkeypatch.setenv("GITHUB_USERNAME", "testuser")

        class GitHubSecrets(TaskSecrets):
            github_token: str
            github_username: str

        secrets = GitHubSecrets()
        assert secrets.github_token == "gh_token"
        assert secrets.github_username == "testuser"

    def test_missing_required_field_raises_error(self) -> None:
        """Test that missing required fields raise ValidationError."""

        class MyTaskSecrets(TaskSecrets):
            required_field: str

        with pytest.raises(ValidationError):
            MyTaskSecrets()

    def test_optional_field_with_default(self) -> None:
        """Test that optional fields with defaults work."""

        class MyTaskSecrets(TaskSecrets):
            required_field: str = "default_value"

        secrets = MyTaskSecrets()
        assert secrets.required_field == "default_value"
