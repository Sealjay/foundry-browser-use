# CLAUDE.md

This project uses Browser Use with Microsoft Foundry for browser automation.

## Commands
- Deploy infra (CLI): `./infra/deploy.sh <resource-group> [location] [account-name]`
- Deploy infra (Bicep): `./infra/deploy-bicep.sh <resource-group>`
- Teardown infra: `./infra/teardown.sh <resource-group>`
- Run interactive CLI: `uv run python browse.py`
- Run example: `uv run python agent.py`
- Run custom task: `uv run python run_task.py "your task here"`
- Lint: `uv run ruff check .`
- Format: `uv run ruff format .`

## Architecture
- infra/ contains Azure CLI and Bicep deployment scripts for the Foundry resource
- browser-use handles Playwright browser control and DOM extraction
- ChatAzureOpenAI (from browser_use) provides the LLM interface to Azure OpenAI via a Foundry resource
- DOM-only mode (use_vision=False) is default for speed and cost efficiency
- browser_agent/ contains the interactive CLI implementation:
  - cli.py - Main CLI orchestrator with interactive loop
  - runner.py - Agent execution wrapper with callbacks and step tracking
  - intervention.py - Human intervention handlers for auth, CAPTCHA, choices, confirmations, stuck states, and step limits
  - keyboard.py - Keyboard shortcuts and agent state for interactive control (AgentState, KeyHandler, build_toolbar)
  - display.py - Result formatting and terminal output
  - session.py - Multi-turn session management with task recording and context injection
- browse.py is the entry point for the interactive CLI
- rich library provides terminal UI components (prompts, tables, colours)
- prompt_toolkit provides keyboard input handling, bottom toolbar, and async prompts during agent execution

## Conventions
- UV for package management, Ruff for linting and formatting
- Python 3.12
- British English in all documentation and comments
- No em dashes - use hyphens
- Shell scripts in infra/ use bash with set -euo pipefail
