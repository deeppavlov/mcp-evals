# Agent notes

## Python version and core dependencies

- **Python**: `>=3.13`
- **Runtime (core)**: `pydantic-ai`, `pydantic-settings`, `loguru`
- **Optional extras**: `domain-filesystem`, `domain-postgres` — see `[project.optional-dependencies]` for pre-built contrib domains.
- **Dev tools**: `pytest`, `mypy`, `ruff`, and related stubs

Use `uv sync` for the project plus the default `dev` dependency group (`uv sync --no-dev` omits it). For parity with CI (all optional extras and all dependency groups), use `uv sync --all-groups --all-extras`.

## Commands (uv)

From the repository root:

```bash
uv sync
```

```bash
uv run pytest
uv run mypy .
uv run ruff check --fix
uv run ruff format
```

CI installs with `uv sync --all-groups --all-extras` before running the configured test command.

## Documentation

- **Project overview and usage**: [README.md](./README.md)
- **Adding tasks and related guidance**: [docs/adding_new_tasks.md](./docs/adding_new_tasks.md)
