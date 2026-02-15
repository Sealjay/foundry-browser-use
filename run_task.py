"""Run a custom browser automation task via command line.

This module allows you to execute arbitrary browser automation tasks using
the Browser Use library with Azure OpenAI. Provide your task as a command-line
argument and the agent will attempt to complete it.

Configuration:
    Set the following environment variables (e.g., in a .env file):
    - AZURE_OPENAI_API_KEY: Your Azure OpenAI API key
    - AZURE_OPENAI_ENDPOINT: Your Azure OpenAI endpoint URL
    - AZURE_OPENAI_DEPLOYMENT_NAME: Your model deployment name
    - AZURE_OPENAI_API_VERSION: API version (e.g., "2024-08-01-preview")

Usage:
    $ uv run python run_task.py "Go to example.com and extract the page title"
    $ uv run python run_task.py --json "Search for Python tutorials on YouTube"
"""

import argparse
import asyncio
import sys

from rich.console import Console

from browser_agent.display import ResultFormatter
from browser_agent.intervention import InterventionHandler
from browser_agent.runner import AgentConfig, AgentRunner


async def main() -> None:
    """Run the browser automation agent with a user-provided task."""
    parser = argparse.ArgumentParser(description="Run a browser automation task")
    parser.add_argument("task", help="The browser automation task to execute")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output result as JSON to stdout")
    args = parser.parse_args()

    console = Console(stderr=True) if args.json_output else Console()
    formatter = ResultFormatter(console)
    intervention_handler = InterventionHandler(console)
    runner = AgentRunner(console, intervention_handler)

    config = AgentConfig(task=args.task, max_steps=25, use_vision=False)

    try:
        success, result, steps, elapsed, summary, structured_data, _actions_log = await runner.run(config)
    except KeyboardInterrupt:
        console.print()
        console.print("[yellow]Task interrupted by user[/yellow]")
        sys.exit(1)

    if args.json_output:
        formatter.show_json_result(
            summary=summary or (result or ""),
            structured_data=structured_data,
            steps=steps,
            elapsed=elapsed,
            success=success,
        )
    elif success and result:
        result_data = {"Result": result}
        if summary:
            result_data["Summary"] = summary
        if structured_data:
            result_data.update(structured_data)
        formatter.show_success(steps, elapsed, result_data)
    else:
        console.print(result or "Task failed.")


if __name__ == "__main__":
    asyncio.run(main())
