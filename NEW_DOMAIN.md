## Summary: Domain and Task Pattern (from Filesystem)

### 1. **Core abstractions**

- **`Domain`** (`src/mcp_evals/domain.py`): Async context manager that:
  - Has a `name`
  - Implements `mcp_servers()` → list of MCP server configs
  - Implements `tasks()` → list of `Task` instances
  - Optionally overrides `setup()` / `teardown()` for env (e.g. temp dir)
  - Exposes `toolset` only while the context is active (after MCP servers are connected)

- **`Task`** (`src/mcp_evals/task.py`): Defines a single eval case with:
  - `name`, `goal` (prompt), `evaluators` (tuple of `Evaluator[...]`)
  - Optional `output_type`, `secrets_type`
  - Optional `setup()` / `teardown()` for per-task env (e.g. workspace from a fixture)

---

### 2. **Adding a new domain (filesystem-style)**

1. **Create a contrib package**  
   e.g. `src/mcp_evals/contrib/<domain_name>/`.

2. **Domain class**
   - Subclass `Domain[DomainSecrets]` (or your domain secrets type).
   - Set `name = "<domain_name>"`.
   - Implement `mcp_servers()` (e.g. `MCPServerStdio` for Docker, or other MCP configs).
   - Implement `tasks()` returning a sequence of your domain’s task instances.
   - Override `setup()` / `teardown()` if the domain needs shared env (e.g. a temp dir for filesystem).

3. **Domain-level utilities (optional)**  
   e.g. `utils.py` for fixtures, downloads, workspace prep — used by the domain and by tasks.

4. **Public API**  
   In `contrib/<domain_name>/__init__.py`, export the domain (and any public helpers like `Fixture`).

---

### 3. **Adding tasks for that domain**

1. **Domain-specific base task (optional but recommended)**  
   e.g. `FilesystemTask(Task[TaskSecrets])` in `task.py`:
   - Accepts domain-specific constructor args (e.g. `work_dir: Path`, `fixture: Fixture`).
   - Overrides `setup()` / `teardown()` to do the same preparation/cleanup for every task in that domain (e.g. download fixture, `prepare_workspace` into `work_dir`).

2. **One subfolder per task**  
   Under `tasks/<task_slug>/`:
   - **`task.py`**  
     - Concrete task class (subclass of the domain base task, e.g. `FilesystemTask`).
     - Class attributes: `name`, `goal` (full prompt).
     - `__init__` calls `super().__init__(...)` and sets `self.evaluators = (Evaluator1(...), Evaluator2(...), ...)`.
   - **`constants.py`** (optional)  
     Expected outputs, file lists, counts, etc., shared by the task and its evaluators.
   - **`custom_evaluators/`**  
     - One module per evaluator; each defines an `Evaluator[YourTask, AgentRunResult]` with `evaluate(ctx) -> EvaluatorOutput` (e.g. return `1.0` or `EvaluationReason(value=0.0, reason="...")`).
     - `custom_evaluators/__init__.py` re-exports them so the task can do `from ...custom_evaluators import Eval1, Eval2`.
   - **`utils.py`** (optional)  
     Helpers used only by this task’s evaluators or constants.

3. **Shared evaluators**  
   In `common_evaluators/` at domain level, define reusable evaluators (e.g. `FileExists(path)`, `DirectoryExists(path)`). Tasks and custom evaluators import from there.

4. **Task registration**
   - In `tasks/__init__.py`: import each task class and export it in `__all__`.
   - In the domain’s `tasks()`: instantiate each task with the right args (e.g. `self._tmp_dir`, `Fixture.XXX`) and return them in a list.

---

### 4. **Flow at runtime**

- **Runner** (`DomainRunner`) is created with an agent and a grouper. You call `run(domain, experiment_name=...)` for each domain.
- **`run(domain, experiment_name=...)`**  
  - Enters `domain` (domain `setup` → connect MCP → `domain.toolset` available).  
  - Converts `domain.tasks()` to a pydantic_evals `Dataset` (each task → `Case` with `inputs=task`, `evaluators=task.evaluators`).  
  - For each case, runs `task_lifecycle` (enter task → run agent with `domain.toolset` → run evaluators) then exits task.  
  - Exits domain (disconnect MCP, domain `teardown`).

So: **domain** = MCP env + list of tasks; **task** = prompt + evaluators + optional per-task setup/teardown; **evaluators** = reusable (common_evaluators) or task-specific (custom_evaluators) checks that use `ctx.inputs` (the task instance) to inspect the environment.

---

### 5. **Concrete checklist for a new domain + tasks**

| Step | Where | What |
|------|--------|------|
| 1 | `contrib/<domain>/domain.py` | Subclass `Domain`, set `name`, `mcp_servers()`, `tasks()`, optional `setup`/`teardown`. |
| 2 | `contrib/<domain>/task.py` | (Optional) Base task class with shared `__init__` and `setup`/`teardown`. |
| 3 | `contrib/<domain>/utils.py` | (Optional) Fixtures, downloads, workspace helpers. |
| 4 | `contrib/<domain>/common_evaluators/` | (Optional) Shared evaluators for the domain. |
| 5 | `contrib/<domain>/tasks/<task_slug>/task.py` | Concrete task: `name`, `goal`, `evaluators` in `__init__`. |
| 6 | `contrib/<domain>/tasks/<task_slug>/custom_evaluators/` | Task-specific evaluators; export in `__init__.py`. |
| 7 | `contrib/<domain>/tasks/__init__.py` | Import and export all task classes. |
| 8 | `contrib/<domain>/__init__.py` | Export domain (and e.g. `Fixture`). |
| 9 | Script or runner | Instantiate domain, create `DomainRunner(agent=agent, grouper=PlainGrouper())`, then `await runner.run(domain, experiment_name=...)`. |

This is the pattern used by the filesystem domain and its tasks (e.g. `UppercaseTask`, `TimelineExtractionTask`); you can replicate it for a new domain (e.g. “browser” or “postgres”) by adding a new `contrib/<domain>/` tree and wiring it into the runner the same way.

---

### 6. How to validate during the process

Run the static checks:
```bash
uv run mypy .
uv run ruff check --fix
```
