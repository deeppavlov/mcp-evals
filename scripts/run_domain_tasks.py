#!/usr/bin/env python3
r"""Run contrib domain tasks with an OpenAI-compatible API (pydantic-ai).

Prerequisites:
    Filesystem domain:
        uv sync --extra domain-filesystem
    Or pip:
        pip install 'pydantic-ai-mcp-evals[domain-filesystem]'
    Postgres domain:
        uv sync --extra domain-postgres
        pip install 'pydantic-ai-mcp-evals[domain-postgres]'

Usage:
    # Credentials and optional endpoint (pydantic-ai / OpenAI client env vars)
    export OPENAI_API_KEY="your-api-key"
    export OPENAI_BASE_URL="https://your-custom-endpoint.com/v1"  # optional

    # Default: filesystem domain, model from OPENAI_MODEL or gpt-4o
    uv run python scripts/run_domain_tasks.py

    uv run python scripts/run_domain_tasks.py --domain pg
    uv run python scripts/run_domain_tasks.py --model gpt-4o-mini

Environment variables:
    OPENAI_API_KEY: API key (required for real runs).
    OPENAI_BASE_URL: Base URL for an OpenAI-compatible API (optional).
    OPENAI_MODEL: Model id if --model is not passed (default: gpt-4o).
    DOWNLOAD_PROXY: Optional HTTP(S) proxy for fixture downloads inside contrib domains.
"""

import argparse
import asyncio
import os
from copy import deepcopy
from typing import Any

import logfire
from dotenv import load_dotenv
from loguru import logger
from pydantic_ai import Agent, UsageLimits
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelRequestPart, ToolReturnPart

from mcp_evals import Domain, DomainRunner, PlainGrouper

DEFAULT_MODEL = "gpt-4o"

logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_pydantic_ai()

TOOL_RETURN_LIMIT = 100_000


def intermediate_speculations(thought: str) -> None:  # noqa: ARG001
    """Record intermediate speculations.

    This function is intended to use by AI agents to help them better understand current context.
    It is not necessary to use it after each step.

    Args:
       thought: the thoughts to record.
    """
    return


def truncate_tool_returns(messages: list[ModelMessage]) -> list[ModelMessage]:
    """Truncate overly long tool returns to prevent model fail."""
    res: list[ModelMessage] = []
    for m in messages:
        if not isinstance(m, ModelRequest):
            res.append(m)
            continue
        parts: list[ModelRequestPart] = []
        for p in m.parts:
            if not isinstance(p, ToolReturnPart):
                parts.append(p)
                continue
            if not isinstance(p.content, str):
                parts.append(p)
                continue
            if len(p.content) > TOOL_RETURN_LIMIT:
                logger.warning("Met too long tool return. Truncating...")
                edited_part = deepcopy(p)
                edited_part.content = p.content[:TOOL_RETURN_LIMIT] + "\n[too long... truncated...]"
                parts.append(edited_part)
            else:
                parts.append(p)
        edited_message = deepcopy(m)
        edited_message.parts = parts
        res.append(edited_message)

    return res


def main() -> None:
    """Run contrib domain tasks with OpenAI."""
    parser = argparse.ArgumentParser(
        description="Run filesystem or Postgres contrib domain tasks via an OpenAI-compatible API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help=f"Model name (default: OPENAI_MODEL env or {DEFAULT_MODEL!r})",
    )
    parser.add_argument(
        "--domain",
        type=str,
        choices=["pg", "fs"],
        default="fs",
        help="Domain: 'fs' (filesystem, default) or 'pg' (postgres).",
    )
    parser.add_argument(
        "--experiment-name",
        type=str,
        default=None,
        help="Experiment name. Use it to differentiate runs.",
    )
    parser.add_argument(
        "--max-tasks",
        type=int,
        default=None,
        help="Max number of tasks to run per domain (default: all).",
    )

    args = parser.parse_args()

    load_dotenv()
    model = args.model or os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)

    agent = Agent(
        f"openai:{model}",
        system_prompt=(
            "You are a helpful assistant that can use tools to complete tasks. "
            "You can provide text messages beside the final answer as a means of "
            "intermediate speculations and reasoning."
        ),
        tools=[intermediate_speculations],
        history_processors=[truncate_tool_returns],
    )

    # Create domain and runner
    domain: Domain[Any]
    if args.domain == "pg":
        from mcp_evals.contrib.postgres import PostgresDomain  # noqa: PLC0415

        domain = PostgresDomain()
    elif args.domain == "fs":
        from mcp_evals.contrib.filesystem import FilesystemDomain  # noqa: PLC0415

        domain = FilesystemDomain()

    runner = DomainRunner(
        agent=agent,
        grouper=PlainGrouper(),
        max_tasks=args.max_tasks,
        usage_limits=UsageLimits(request_limit=25),
    )

    logger.info(f"Running {args.domain} tasks with model: {model}")
    if args.max_tasks is not None:
        logger.info(f"Running up to {args.max_tasks} tasks per domain")

    experiment_name = args.experiment_name or f"{args.domain}_run"

    # Run benchmark
    async def run() -> None:
        report = await runner.run(domain, experiment_name=experiment_name)
        logger.info(f"\nDomain: {args.domain}")
        logger.info(f"Total tasks: {len(report.cases)}")

        report.print(include_reasons=True, include_output=True)
        for case in report.cases:
            passed = all(eval_res.value == 1.0 for eval_res in case.scores.values())
            if passed:
                logger.success(f"Task {case.name} passed")
            else:
                logger.warning(f"Task {case.name} failed")

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Run interrupted (Ctrl+C); exiting.")
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
