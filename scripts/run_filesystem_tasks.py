#!/usr/bin/env python3
r"""Script to run all filesystem tasks with OpenAI.

This script runs all filesystem tasks from MCP Universe using an OpenAI-compatible
API endpoint. It uses the mcp-evals library to execute tasks and evaluate results.

Prerequisites:
    Install filesystem domain dependencies:
        uv sync --extra domain-filesystem
    Or with pip:
        pip install 'mcp-evals[domain-filesystem]'

Usage:
    # Set OpenAI API key and base URL via environment variables
    export OPENAI_API_KEY="your-api-key"
    export OPENAI_BASE_URL="https://your-custom-endpoint.com/v1"
    uv run python scripts/run_filesystem_tasks.py

    # Or use command line arguments
    uv run python scripts/run_filesystem_tasks.py \\
        --api-key "your-api-key" \\
        --base-url "https://your-custom-endpoint.com/v1"

    # Specify a different model
    uv run python scripts/run_filesystem_tasks.py \\
        --model "gpt-4o-mini" \\
        --api-key "your-api-key" \\
        --base-url "https://your-custom-endpoint.com/v1"

Environment Variables:
    OPENAI_API_KEY: Your OpenAI API key (required if not provided via --api-key)
    OPENAI_BASE_URL: Custom base URL for OpenAI-compatible API (required if not provided via --base-url)
    OPENAI_MODEL: Model name to use (defaults to "gpt-4o" if not provided)

Examples:
    # Run with default settings (gpt-4o)
    uv run python scripts/run_filesystem_tasks.py

    # Run with a specific model
    OPENAI_MODEL="gpt-4o-mini" uv run python scripts/run_filesystem_tasks.py

    # Run with custom endpoint
    OPENAI_BASE_URL="http://localhost:8000/v1" \\
    OPENAI_API_KEY="dummy-key" \\
    uv run python scripts/run_filesystem_tasks.py
"""

import argparse
import asyncio
import os

from loguru import logger
from pydantic import Field, SecretStr
from pydantic_ai import Agent
from pydantic_settings import BaseSettings, SettingsConfigDict

from mcp_evals import BenchmarkRunner
from mcp_evals.contrib.filesystem import FilesystemDomain


class ScriptSettings(BaseSettings):
    """Settings for the filesystem tasks script, loaded from environment variables."""

    api_key: SecretStr = Field(..., description="OpenAI API key")
    base_url: str = Field(..., description="Custom base URL for OpenAI-compatible API")
    model: str = Field(default="gpt-4.1", description="Model name to use")

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        env_prefix="OPENAI_",
        env_file_encoding="utf-8",
    )

    @property
    def api_key_str(self) -> str:
        """Get the API key as a plain string."""
        return self.api_key.get_secret_value()


def main() -> None:
    """Run all filesystem tasks with OpenAI."""
    parser = argparse.ArgumentParser(
        description="Run filesystem tasks with OpenAI-compatible API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="OpenAI API key (overrides OPENAI_API_KEY env var)",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="Custom base URL for OpenAI API (overrides OPENAI_BASE_URL env var)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model name to use (overrides OPENAI_MODEL env var or 'gpt-4.1' default)",
    )

    args = parser.parse_args()

    # Load settings from environment
    settings = ScriptSettings()

    # Override with command-line arguments if provided
    api_key = args.api_key or settings.api_key_str
    base_url = args.base_url or settings.base_url
    model = args.model or settings.model

    # Set environment variables for pydantic_ai (it reads these for OpenAI client config)
    os.environ["OPENAI_API_KEY"] = api_key
    os.environ["OPENAI_BASE_URL"] = base_url

    # Create agent with custom base URL
    agent = Agent(
        f"openai:{model}",
        system_prompt="You are a helpful assistant that can use filesystem tools to complete tasks.",
    )

    # Create domain and runner
    domain = FilesystemDomain()
    runner = BenchmarkRunner(agent=agent, domains=[domain])

    logger.info(f"Running filesystem tasks with model: {model}")
    logger.info(f"Using base URL: {base_url}")

    # Run benchmark
    async def run() -> None:
        reports = await runner.run()
        for report in reports:
            logger.info("\nDomain: filesystem")
            logger.info(f"Total tasks: {len(report.cases)}")

            # Count passed cases (check if all evaluators passed)
            passed_count = 0
            for case in report.cases:
                # Check if all evaluator outputs indicate success
                all_passed = (
                    all(getattr(eval_output, "value", 0.0) >= 1.0 for eval_output in case.evaluator_outputs)
                    if hasattr(case, "evaluator_outputs")
                    else False
                )
                if all_passed:
                    passed_count += 1

            logger.info(f"Passed: {passed_count}/{len(report.cases)}")
            logger.info("\nTask Results:")
            for case in report.cases:
                # Check if all evaluators passed
                all_passed = (
                    all(getattr(eval_output, "value", 0.0) >= 1.0 for eval_output in case.evaluator_outputs)
                    if hasattr(case, "evaluator_outputs")
                    else False
                )
                status = "✓" if all_passed else "✗"
                logger.info(f"  {status} {case.name}")
                if not all_passed and hasattr(case, "evaluator_outputs"):
                    for i, eval_output in enumerate(case.evaluator_outputs):
                        value = getattr(eval_output, "value", 0.0)
                        if value < 1.0:
                            reason = getattr(eval_output, "reason", f"Evaluator {i + 1} failed")
                            logger.info(f"    - {reason}")

    asyncio.run(run())


if __name__ == "__main__":
    main()
