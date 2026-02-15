#!/usr/bin/env python3
"""Browse - Interactive CLI for AI browser automation."""

import argparse
import asyncio

from browser_agent.cli import run_cli


def main() -> None:
    """Parse arguments and run the interactive CLI."""
    parser = argparse.ArgumentParser(description="Browse - AI browser automation")
    parser.add_argument("--verbose", action="store_true", help="Show detailed agent actions during execution")
    args = parser.parse_args()

    asyncio.run(run_cli(verbose=args.verbose))


if __name__ == "__main__":
    main()
