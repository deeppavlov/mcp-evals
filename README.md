# MCP Evals

A code-first evaluation framework for testing LLM agents' ability to use MCP (Model Context Protocol) tools and accomplish tasks.

## Overview

This library provides infrastructure for running structured evaluations of LLM agents against MCP-enabled environments. Each task is defined by:

- **Domain**: A collection of MCP servers providing tools
- **Goal**: A text-described objective for the agent
- **Evaluators**: Functions that verify task completion and compute metrics

## Key Principles

| Principle | Implementation |
|-----------|----------------|
| **Code-first** | All tasks defined in Python, no YAML/JSON configs |
| **Simple user API** | Users define domains and tasks; library handles orchestration |
| **No wheel reinvention** | pydantic-ai for LLM + MCP, pydantic_evals for evaluation, logfire for observability |
| **Resource lifecycle** | Async context managers with safe cleanup |
| **Dependency injection** | Dishka for resource acquisition and cleanup |
| **Maintainability** | pytest, mypy, ruff |

## Prerequisites

### uv (for running MCP servers)

Many MCP servers are distributed as Python packages and run via `uvx` (part of [uv](https://github.com/astral-sh/uv)). `uvx` runs CLI tools in isolated environments without global installation — similar to `npx` for Node.js.

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Now you can run MCP servers like:
uvx mcp-server-filesystem /workspace
uvx mcp-server-sqlite test.db
```

MCP servers are available from:
- [Official MCP servers](https://github.com/modelcontextprotocol/servers)
- PyPI (search for `mcp-server-*`)

## Quick Start

```python
from mcp_evals import BenchmarkRunner, Domain, Task
from mcp_evals.evaluators import FileExists
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio

# Simple task as class with attributes
class CreateConfigTask(Task):
    name = "create_config"
    goal = "Create a config.json file with default settings"
    evaluators = [FileExists("config.json")]

class CreateReadmeTask(Task):
    name = "create_readme"
    goal = "Create a README.md with project description"
    evaluators = [FileExists("README.md")]

class FilesystemDomain(Domain):
    name = "filesystem"
    
    def mcp_servers(self):
        return [MCPServerStdio("uvx", "mcp-server-filesystem", "/workspace")]
    
    def tasks(self):
        return [CreateConfigTask(), CreateReadmeTask()]

async def main():
    agent = Agent("openai:gpt-4o")
    runner = BenchmarkRunner(agent=agent, domains=[FilesystemDomain()])
    report = await runner.run()
    report.print()
```

## Usage

### 1. Define Tasks

Tasks are abstract async context managers that define what the agent should accomplish and how to verify it:

```python
from mcp_evals import Task
from mcp_evals.evaluators import SQLQueryReturns

class CreateUsersTableTask(Task):
    name = "create_users_table"
    goal = "Create a users table with id, name, and email columns"
    evaluators = [
        SQLQueryReturns(
            query="SELECT name FROM sqlite_master WHERE type='table'",
            expected=["users"],
        ),
    ]

class InsertUserTask(Task):
    name = "insert_user"
    goal = "Insert a user named 'Alice' with email 'alice@example.com'"
    evaluators = [
        SQLQueryReturns(
            query="SELECT name, email FROM users",
            expected=[("Alice", "alice@example.com")],
        ),
    ]
```

### 2. Define a Domain

A domain encapsulates an environment (MCP servers) and groups related tasks:

```python
from mcp_evals import Domain
from pydantic_ai.mcp import MCPServerStdio

class DatabaseDomain(Domain):
    name = "database"
    
    def mcp_servers(self):
        return [MCPServerStdio("uvx", "mcp-server-sqlite", "test.db")]
    
    def tasks(self):
        return [CreateUsersTableTask(), InsertUserTask()]
```

### 3. Run the Benchmark

```python
from mcp_evals import BenchmarkRunner
from pydantic_ai import Agent
import logfire

logfire.configure()

async def main():
    agent = Agent(
        "openai:gpt-4o",
        system_prompt="You are a helpful assistant.",
    )
    
    runner = BenchmarkRunner(
        agent=agent,
        domains=[FilesystemDomain(), DatabaseDomain()],
    )
    
    report = await runner.run()
    report.print()
    
    # Access detailed results
    for result in report.results:
        print(f"{result.task_name}: {'✓' if result.passed else '✗'}")
        for metric in result.metrics:
            print(f"  {metric.name}: {metric.value}")
```

### 4. Custom Evaluators

Create domain-specific evaluators using `pydantic_evals` base classes:

```python
from pydantic_evals.evaluators import Evaluator, EvaluatorContext
from pydantic_evals import EvaluatorOutput, EvaluationReason

class APIResponseContains(Evaluator[TaskInput, TaskOutput]):
    endpoint: str
    expected_field: str
    
    async def evaluate(
        self, ctx: EvaluatorContext[TaskInput, TaskOutput]
    ) -> EvaluatorOutput:
        # Access the task output
        response = ctx.output
        
        if self.expected_field in response:
            return 1.0
        else:
            return EvaluationReason(
                value=0.0,
                reason=f"Field '{self.expected_field}' not found in response",
            )
```

See [pydantic_evals documentation](https://ai.pydantic.dev/evals/) for more details on evaluator types and context.

### 5. Tasks with Lifecycle (Setup/Teardown)

Tasks can implement `setup()` for initialization and use `AsyncExitStack` for clean resource management:

```python
from contextlib import AsyncExitStack
from pathlib import Path
import aiofiles.tempfile
import os

from mcp_evals import Task
from mcp_evals.evaluators import FileExists, ContentMatches

class MusicReportTask(Task):
    name = "music_report"
    goal = "Analyze the music files and create music_analysis_report.txt"
    evaluators = [
        FileExists("music/music_analysis_report.txt"),
        ContentMatches("music/music_analysis_report.txt", pattern=r"晴天.*2\.576"),
    ]
    
    _stack: AsyncExitStack | None = None  # Track context state
    
    async def setup(self) -> None:
        # Prevent re-entry
        if self._stack is not None:
            raise RuntimeError(f"Task {self.name} context already entered")
        
        self._stack = AsyncExitStack()
        await self._stack.__aenter__()
        
        # Create temp directory using async context manager
        temp_dir_ctx = aiofiles.tempfile.TemporaryDirectory()
        self.test_dir = Path(await self._stack.enter_async_context(temp_dir_ctx))
        
        # Download and extract test fixtures
        archive_path = await download_fixtures("music_collection.tar.gz")
        self._stack.callback(lambda: archive_path.unlink(missing_ok=True))
        
        await extract_archive(archive_path, self.test_dir)
        
        # Set environment variable for MCP server (will be cleared on teardown)
        old_value = os.environ.get("FILESYSTEM_ROOT")
        os.environ["FILESYSTEM_ROOT"] = str(self.test_dir)
        self._stack.callback(lambda: self._restore_env("FILESYSTEM_ROOT", old_value))
    
    async def teardown(self) -> None:
        if self._stack is not None:
            await self._stack.aclose()
            self._stack = None
    
    @staticmethod
    def _restore_env(key: str, old_value: str | None) -> None:
        if old_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old_value
```

### 6. Tasks with Secrets

Use pydantic-settings for type-safe secret management:

```python
from pydantic_settings import BaseSettings
from mcp_evals import Task, TaskSecrets

class GitHubSecrets(TaskSecrets):
    github_token: str
    github_username: str

class CreateRepoTask(Task):
    name = "create_repo"
    goal = "Create a GitHub repository named 'test-repo' with a README"
    evaluators = [RepoExists("test-repo"), FileInRepoExists("test-repo", "README.md")]
    secrets_type = GitHubSecrets  # Declares which secrets this task needs
    
    async def setup(self) -> None:
        # Secrets are loaded automatically from environment
        print(f"Will create repo under: {self.secrets.github_username}")
    
    async def teardown(self) -> None:
        # Clean up: delete the repo created during the task
        await delete_github_repo(
            repo="test-repo",
            token=self.secrets.github_token,
        )
```

### 7. Tasks with Dynamic Goals (Templating)

Use `@property` for dynamic goal generation:

```python
class ParameterizedTask(Task):
    name = "create_config"
    evaluators = [FileExists("config.json"), JsonFieldEquals("config.json", "port", 8080)]
    
    def __init__(self, app_name: str, port: int = 8080):
        self.app_name = app_name
        self.port = port
    
    @property
    def goal(self) -> str:
        return f"Create config.json with app_name='{self.app_name}' and port={self.port}"

# Usage in domain:
class MyDomain(Domain):
    def tasks(self):
        return [
            ParameterizedTask("web-server", port=3000),
            ParameterizedTask("api-gateway", port=8080),
        ]
```

## Architecture

### High-Level Flow

```mermaid
flowchart TB
    subgraph Benchmark["Benchmark Run"]
        subgraph Domain1["Domain: filesystem"]
            MCP1[MCP Servers]
            Toolset1[Combined Toolset]
            Tasks1[Tasks]
            MCP1 --> Toolset1
            
            subgraph Task1["Task Execution"]
                Agent1[Agent]
                Goal1[Goal + Evaluators]
                Agent1 --> |accomplishes| Goal1
            end
            
            Tasks1 --> Goal1
            Toolset1 --> Agent1
        end
        
        subgraph Domain2["Domain: database"]
            MCP2[MCP Servers]
            Toolset2[Combined Toolset]
            Tasks2[Tasks]
            MCP2 --> Toolset2
            
            subgraph Task2["Task Execution"]
                Agent2[Agent]
                Goal2[Goal + Evaluators]
                Agent2 --> |accomplishes| Goal2
            end
            
            Tasks2 --> Goal2
            Toolset2 --> Agent2
        end
    end
```

### Evaluation Pipeline

```mermaid
sequenceDiagram
    participant U as User Code
    participant R as BenchmarkRunner
    participant D as Domain
    participant A as Agent
    participant MCP as MCP Servers
    participant E as Evaluator
    participant LF as Logfire

    U->>R: runner.run()
    
    loop For each domain
        R->>D: domain.mcp_servers()
        R->>MCP: Connect to MCP servers
        MCP-->>R: Combined toolset
        R->>D: domain.tasks()
        
        loop For each task
            R->>A: agent.run(task.goal, tools=toolset)
            A->>LF: Log agent span
            A->>MCP: Use tools
            MCP-->>A: Tool results
            A-->>R: Agent output
            
            R->>E: evaluator.evaluate(context)
            E->>LF: Log evaluator span
            E->>MCP: Check environment state
            E-->>R: EvaluatorOutput
        end
        
        R->>MCP: Disconnect servers
    end
    
    R-->>U: BenchmarkReport
```

### Integration with pydantic_evals

Internally, each domain is converted to a `pydantic_evals.Dataset`. Here's how the mapping works:

```mermaid
flowchart LR
    subgraph "mcp_evals (User API)"
        Domain --> Tasks[Task instances]
    end
    
    subgraph "pydantic_evals (Internal)"
        Dataset --> Cases[Case instances]
        Dataset --> EvalFn[Evaluated Function]
    end
    
    Domain -->|"converted to"| Dataset
    Tasks -->|"converted to"| Cases
    
    subgraph "Each Case"
        CaseInputs["inputs: Task (the instance itself)"]
        CaseEvals[evaluators: task.evaluators]
    end
```

#### Conversion: Domain → Dataset, Task → Case

The key insight: `Case.inputs` accepts any type, so we pass the `Task` instance directly. Evaluators receive this in their context, giving them full access to task attributes.

```python
# mcp_evals/_internal/conversion.py

from typing import TypeVar
from pydantic_evals import Dataset, Case
from pydantic_ai.result import RunResult

from mcp_evals import Task, Domain

TaskT = TypeVar("TaskT", bound=Task)
OutputT = TypeVar("OutputT")  # Will be RunResult[ResponseT]

def domain_to_dataset(domain: Domain) -> Dataset[Task, RunResult]:
    """Convert mcp_evals Domain to pydantic_evals Dataset."""
    cases = [
        Case(
            name=task.name,
            inputs=task,  # Task instance is the input — evaluators access it via ctx.inputs
            evaluators=task.evaluators,
        )
        for task in domain.tasks()
    ]
    return Dataset(cases=cases)
```

#### The Evaluated Function

The library defines an internal "evaluated function" that `pydantic_evals` calls for each case. This function:

1. Enters the **Task context** (`__aenter__`) for setup
2. Gets **Agent** (BENCHMARK-scoped) and **CombinedToolset** from Dishka (DOMAIN-scoped)
3. Runs the agent with the goal and toolset
4. Exits the task context (`__aexit__`) for teardown
5. Returns `RunResult` directly for evaluation

```python
# mcp_evals/_internal/evaluated_fn.py

from typing import TypeVar
from dishka import FromDishka
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.toolsets import CombinedToolset
from pydantic_ai.result import RunResult

from mcp_evals import Task

OutputT = TypeVar("OutputT")

async def run_agent_on_task(
    task: Task,
    *,
    # Dishka injects these from DOMAIN scope
    agent: FromDishka[Agent],
    toolset: FromDishka[CombinedToolset],  # AsyncIterator provider with cleanup
) -> RunResult[OutputT]:
    """
    The function evaluated by pydantic_evals for each Case.
    
    This is where mcp_evals integrates with:
    - Task lifecycle (async context manager for setup/teardown)
    - Dishka (CombinedToolset from DOMAIN scope, Agent from BENCHMARK scope)
    
    Evaluators receive:
    - ctx.inputs: the Task instance (access task.goal, task.secrets, etc.)
    - ctx.output: the RunResult from agent.run()
    """
    # Enter task context (calls task.setup())
    async with task:
        # Run the agent with domain's combined toolset
        result: RunResult[OutputT] = await agent.run(
            task.goal,
            output_type=task.output_type,
            toolsets=[toolset],
        )
        return result
    # Task context exits here (calls task.teardown())
```

#### Dishka Provider for CombinedToolset

The `CombinedToolset` is provided at DOMAIN scope using an `AsyncIterator` provider, ensuring proper cleanup:

```python
# mcp_evals/_internal/providers.py

from dishka import Provider, Scope, provide
from pydantic_ai import CombinedToolset

class DomainProvider(Provider):
    scope = Scope.DOMAIN
    
    @provide
    async def combined_toolset(
        self, 
        mcp_servers: list[MCPServerStdio],  # From domain.mcp_servers()
    ) -> AsyncIterator[CombinedToolset]:
        """
        Provide CombinedToolset with automatic cleanup.
        
        AsyncIterator provider pattern ensures proper closing of MCP connections.
        """
        toolset = CombinedToolset(mcp_servers)
        async with toolset:
            yield toolset
```

#### Dataset Evaluation in BenchmarkRunner

```python
# mcp_evals/_internal/runner.py (simplified)

async def run_domain(domain: Domain, container: AsyncContainer) -> EvalReport:
    """Run all tasks in a domain."""
    
    # Convert domain to pydantic_evals Dataset
    dataset = domain_to_dataset(domain)
    
    # Create evaluated function with Dishka injection
    # (pydantic_evals supports dependency injection via function signature)
    evaluated_fn = inject(run_agent_on_task, container)
    
    # Run evaluation — pydantic_evals handles the loop
    report = await dataset.evaluate(
        evaluated_fn,
        max_concurrency=1,  # Sequential by default for stateful tasks
    )
    
    return report
```

### Scope Lifecycle

The library manages resource lifecycle at two levels:

| Scope | Managed By | Lifecycle | Resources |
|-------|------------|-----------|-----------|
| `BENCHMARK` | Dishka | Entire evaluation run | Agent, global config, logfire client |
| `DOMAIN` | Dishka | Per domain | MCP connections, CombinedToolset |
| Task | `async with task:` | Per task execution | Temp files, env vars, fixtures |

**Dishka scopes** manage shared resources (Agent, MCP connections) with automatic cleanup via `AsyncIterator` providers.

**Task context managers** handle task-specific setup/teardown (fixtures, environment) with `AsyncExitStack` for safe cleanup.

Users don't need to manage these scopes directly—`BenchmarkRunner` handles everything.

## Project Structure

```
mcp-evals/
├── src/mcp_evals/
│   ├── __init__.py           # Public API: Domain, Task, BenchmarkRunner, etc.
│   ├── domain.py             # Domain ABC
│   ├── task.py               # Task ABC (async context manager)
│   ├── secrets.py            # TaskSecrets base class
│   ├── runner.py             # BenchmarkRunner facade
│   ├── evaluators/
│   │   ├── __init__.py       # Public evaluators
│   │   └── builtin.py        # FileExists, ContentMatches, SQLQueryReturns, etc.
│   ├── _internal/
│   │   ├── scopes.py         # Dishka scope definitions (BENCHMARK, DOMAIN)
│   │   ├── providers.py      # DI providers (Agent, CombinedToolset)
│   │   ├── container.py      # Container factory
│   │   ├── conversion.py     # Domain → Dataset, Task → Case conversion
│   │   └── evaluated_fn.py   # run_agent_on_task() for pydantic_evals
│   └── contrib/              # Pre-built domains (optional)
│       ├── filesystem.py
│       └── sqlite.py
├── examples/
│   ├── filesystem_eval/
│   └── database_eval/
└── tests/
```

## API Reference

### `Domain` (ABC)

```python
class Domain(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique domain identifier."""

    @abstractmethod
    def mcp_servers(self) -> list[MCPServerStdio | MCPServerHTTP]:
        """Return MCP server configurations."""

    @abstractmethod
    def tasks(self) -> list[Task]:
        """Return Task instances to evaluate in this domain."""
```

### `Task` (ABC + Async Context Manager)

```python
from abc import ABC
from contextlib import AbstractAsyncContextManager
from functools import cached_property
from typing import ClassVar, Sequence

from pydantic_settings import BaseSettings


class TaskSecrets(BaseSettings):
    """Base for task-specific secrets. Override in subclasses."""
    model_config = {"extra": "ignore", "env_file": ".env"}


class Task(AbstractAsyncContextManager, ABC):
    """
    Abstract base for evaluation tasks.
    
    Required attributes (class attributes or @property):
        name: str                    - Unique task identifier
        goal: str                    - Prompt/instruction for the agent
        evaluators: Sequence[Evaluator] - Verification functions
    
    Optional attributes:
        output_type: type | None     - Pydantic model for structured output
        secrets_type: ClassVar[type] - BaseSettings subclass for secrets
    
    Lifecycle methods (override as needed):
        setup()    - Called on __aenter__, before agent runs
        teardown() - Called on __aexit__, after agent completes
    """
    
    # === Required (implement as class attr or @property) ===
    name: str
    goal: str
    evaluators: Sequence["Evaluator"]
    
    # === Optional with defaults ===
    output_type: type | None = None
    secrets_type: ClassVar[type[TaskSecrets]] = TaskSecrets
    
    # === Secrets access ===
    @cached_property
    def secrets(self) -> TaskSecrets:
        """Load and cache secrets from environment."""
        return self.secrets_type()
    
    # === Lifecycle (default implementations) ===
    async def __aenter__(self) -> "Task":
        await self.setup()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool | None:
        await self.teardown()
        return None
    
    async def setup(self) -> None:
        """Override to perform setup before agent execution."""
        pass
    
    async def teardown(self) -> None:
        """Override to perform cleanup after agent execution."""
        pass
```

### `TaskSecrets` (BaseSettings)

```python
from pydantic_settings import BaseSettings

class TaskSecrets(BaseSettings):
    """
    Base class for task-specific secrets.
    
    Subclass to declare required environment variables:
    
        class MySecrets(TaskSecrets):
            api_key: str           # Required: MYAPI_KEY env var
            timeout: int = 30      # Optional with default
    
    Then reference in Task:
    
        class MyTask(Task):
            secrets_type = MySecrets
            
            async def setup(self):
                print(self.secrets.api_key)  # Type-safe access
    """
    model_config = {"extra": "ignore", "env_file": ".env"}
```

### `BenchmarkRunner`

```python
class BenchmarkRunner:
    def __init__(
        self,
        agent: Agent,
        domains: list[Domain],
    ) -> None: ...

    async def run(self) -> BenchmarkReport:
        """Run all tasks from all domains."""
        ...
```

### Evaluators

This library uses [pydantic_evals](https://ai.pydantic.dev/evals/) for evaluation infrastructure. Key types:

- `Evaluator[InputT, OutputT]` — Base class for custom evaluators
- `EvaluatorContext[InputT, OutputT]` — Context passed to evaluators with input/output data
- `EvaluatorOutput` — Result containing score, reason, and optional labels

See `mcp_evals.evaluators` for built-in evaluators.

## Built-in Evaluators

TODO

## Pre-built Domains

TODO

## Dependencies

- **[pydantic-ai](https://ai.pydantic.dev/)** — LLM provider abstraction + MCP client
- **[pydantic-evals](https://ai.pydantic.dev/evals/)** — Evaluation infrastructure (Dataset, Case, Evaluator)
- **[pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)** — Environment-based secrets management
- **[logfire](https://pydantic.dev/logfire)** — Observability and tracing
- **[dishka](https://github.com/reagento/dishka)** — Dependency injection and resource lifecycle (internal)

## Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Type checking
uv run mypy src/

# Linting
ruff check --fix
ruff format
```
