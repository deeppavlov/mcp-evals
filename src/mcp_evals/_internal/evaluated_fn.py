"""The function evaluated by pydantic_evals for each Case."""

from typing import Any

from pydantic_ai.agent import Agent
from pydantic_ai.output import OutputDataT
from pydantic_ai.run import AgentRunResult
from pydantic_ai.toolsets import CombinedToolset

from mcp_evals.task import Task
from mcp_evals.types import DepsMaker


async def run_agent_on_task(
    task: Task[Any, OutputDataT],
    *,
    agent: Agent[Any, Any],
    toolset: CombinedToolset[Any],
    deps_maker: DepsMaker,
) -> AgentRunResult[OutputDataT]:
    """The function evaluated by pydantic_evals for each Case.

    Agent and toolset are bound via `functools.partial` before passing
    to `dataset.evaluate()`. Deps are obtained by entering the async context
    manager returned by deps_maker(task); that CM is entered and exited
    for each task so each task gets fresh deps.

    Note: Task context (setup/teardown) is managed by `case_context_manager`,
    not inside this function. This ensures evaluators can access task state
    before teardown runs.

    Evaluators receive:
    - `ctx.inputs`: the `Task` instance (access `task.goal`, `task.secrets`, etc.)
    - `ctx.output`: the result from `agent.run()`
    """
    async with deps_maker(task) as deps:
        return await agent.run(
            task.goal,
            output_type=task.output_type,
            toolsets=[toolset, *task.mcp_servers()],
            deps=deps,
        )
