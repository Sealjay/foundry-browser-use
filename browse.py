#!/usr/bin/env python3
"""Browse - Interactive CLI for AI browser automation."""

import argparse
import asyncio
import logging

from browser_agent.cli import run_cli

# Suppress noisy tracebacks from browser-use's internal event bus and watchdogs.
# Screenshot timeouts on heavy pages are recoverable and clutter the output.
logging.getLogger("bubus").setLevel(logging.CRITICAL)
logging.getLogger("browser_use.browser.watchdog_base").setLevel(logging.WARNING)
logging.getLogger("BrowserSession").setLevel(logging.WARNING)


def main() -> None:
    """Parse arguments and run the interactive CLI."""
    parser = argparse.ArgumentParser(description="Browse - AI browser automation")
    parser.add_argument("--verbose", action="store_true", help="Show detailed agent actions during execution")
    args = parser.parse_args()

    asyncio.run(run_cli(verbose=args.verbose))


if __name__ == "__main__":
    main()
