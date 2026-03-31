"""The function evaluated by pydantic_evals for each Case."""

import asyncio
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

import logfire
from loguru import logger
from pydantic_ai.agent import Agent
from pydantic_ai.output import OutputDataT
from pydantic_ai.run import AgentRunResult
from pydantic_ai.toolsets import CombinedToolset
from pydantic_ai.usage import UsageLimits
from pydantic_evals.evaluators import EvaluationReason, EvaluatorOutput

from mcp_evals.task import Task
from mcp_evals.types import DepsMaker, RunResultProcessor

if TYPE_CHECKING:
    from pydantic_ai.messages import ModelMessage


def _eval_failed(outcome: EvaluatorOutput) -> bool:
    """Return True if evaluator outcome indicates failure."""
    if isinstance(outcome, EvaluationReason):
        val = outcome.value
        return val < 1.0 if isinstance(val, (int, float)) else True
    if isinstance(outcome, (int, float)):
        return outcome < 1.0
    return True


def _get_failure_reason(outcome: EvaluatorOutput) -> str:
    """Extract human-readable reason from evaluator outcome."""
    if isinstance(outcome, EvaluationReason) and outcome.reason:
        return outcome.reason
    if isinstance(outcome, (int, float)):
        return f"Score: {outcome} (expected 1.0)"
    return "Evaluation failed"


async def run_agent_on_task(
    task: Task[Any, OutputDataT],
    *,
    agent: Agent[Any, Any],
    toolset: CombinedToolset[Any],
    deps_maker: DepsMaker,
    run_result_processor: RunResultProcessor | None = None,
    usage_limits: UsageLimits | None = None,
) -> AgentRunResult[OutputDataT]:
    """The function evaluated by pydantic_evals for each Case.

    Agent and toolset are bound via `functools.partial` before passing
    to `dataset.evaluate()`. Deps are obtained by entering the async context
    manager returned by deps_maker(task); that CM is entered and exited
    for each task so each task gets fresh deps.

    Note: Task context (setup/teardown) is managed by pydantic_evals
    `pydantic_evals.lifecycle.CaseLifecycle` (registered on `Dataset.evaluate`),
    not inside this function. This ensures evaluators can access task state
    before teardown runs.

    Evaluators receive:
    - `ctx.inputs`: the `Task` instance (access `task.goal`, `task.secrets`, etc.)
    - `ctx.output`: the result from `agent.run()`
    """
    async with deps_maker(task) as deps:
        result = await agent.run(
            task.goal,
            output_type=task.output_type,
            toolsets=[toolset, *task.mcp_servers()],
            deps=deps,
            usage_limits=usage_limits,
        )
        if run_result_processor is not None:
            await run_result_processor(task, result, deps)
        return result


async def run_agent_on_task_with_self_correction(
    task: Task[Any, OutputDataT],
    *,
    agent: Agent[Any, Any],
    toolset: CombinedToolset[Any],
    deps_maker: DepsMaker,
    run_result_processor: RunResultProcessor | None = None,
    usage_limits: UsageLimits | None = None,
    max_retries: int = 3,
) -> AgentRunResult[OutputDataT]:
    """Run agent on task with self-correction: re-run on evaluator failures with feedback.

    Runs the agent, evaluates with task.evaluators, and if any evaluator fails,
    augments the goal with the failure reasons and retries. Continues until all
    evaluators pass or max_retries is reached.

    Task context (setup/teardown) is managed by CaseLifecycle, not here.
    Evaluators use ctx.inputs (task) and ctx.output (result); we use a minimal
    SimpleNamespace for ctx since EvaluatorContext has many internal fields.
    """
    inputs = task.goal
    result: AgentRunResult[OutputDataT] | None = None
    message_history: list[ModelMessage] = []

    async with deps_maker(task) as deps:
        for attempt in range(max_retries):
            result = await agent.run(
                inputs,
                output_type=task.output_type,
                toolsets=[toolset, *task.mcp_servers()],
                deps=deps,
                usage_limits=usage_limits,
                message_history=message_history,
            )
            if run_result_processor is not None:
                await run_result_processor(task, result, deps)

            with logfire.suppress_instrumentation():
                ctx = SimpleNamespace(inputs=task, output=result)
                failures: list[tuple[str, str]] = []
                for evaluator in task.evaluators:
                    raw = evaluator.evaluate(cast("Any", ctx))
                    outcome = cast(
                        "EvaluatorOutput",
                        await raw if asyncio.iscoroutine(raw) else raw,
                    )
                    if _eval_failed(outcome):
                        name = evaluator.get_serialization_name()
                        failures.append((name, _get_failure_reason(outcome)))

            if not failures:
                return result

            if attempt < max_retries - 1:
                inputs = (
                    "Evaluation results:\n"
                    + "\n".join(f"- {name}: {reason}" for name, reason in failures)
                    + "\n\nPlease, try to fix these errors."
                )
                message_history = result.all_messages()
                logger.debug(f"[{task.name}] Self-correction attempt {attempt + 1} failed, retrying with feedback")

    if result is None:
        msg = "run_agent_on_task_with_self_correction: no result after retries"
        raise RuntimeError(msg)
    return result
