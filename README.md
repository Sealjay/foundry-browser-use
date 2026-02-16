# foundry-browser-use

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=ffffff)](https://www.python.org/)
[![Microsoft Foundry](https://img.shields.io/badge/Microsoft_Foundry-0078D4?logo=microsoftazure&logoColor=ffffff)](https://learn.microsoft.com/azure/ai-foundry/what-is-foundry?WT.mc_id=AI-MVP-5004204)
[![Browser Use](https://img.shields.io/badge/Browser_Use-0.11-FF6B35?logo=googlechrome&logoColor=ffffff)](https://github.com/browser-use/browser-use)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/github/license/Sealjay/foundry-browser-use)](LICENCE)
[![GitHub issues](https://img.shields.io/github/issues/Sealjay/foundry-browser-use)](https://github.com/Sealjay/foundry-browser-use/issues)
[![GitHub stars](https://img.shields.io/github/stars/Sealjay/foundry-browser-use?style=social)](https://github.com/Sealjay/foundry-browser-use)

Interactive AI browser automation using [Browser Use](https://github.com/browser-use/browser-use) and [Microsoft Foundry](https://learn.microsoft.com/azure/ai-foundry/what-is-foundry?WT.mc_id=AI-MVP-5004204). Natural language browser agent with human-in-the-loop intervention points for authentication, verification, and confirmation. DOM-first agent powered by OpenAI models on Microsoft Foundry, controlling Chromium directly via CDP (Chrome DevTools Protocol) for web task automation.

Microsoft Foundry provides managed OpenAI model hosting on Azure with enterprise features like quota management, regional deployment, and integration with Azure's identity and networking stack.

## Quick start

> **Requires Azure setup first.** You'll need a Microsoft Foundry deployment before running the agent - see [Setup](#setup) below.

```bash
uv run python browse.py
```

```
Browse - AI browser automation

What would you like to do?
> Check bbc.co.uk for the top 5 news stories and list them out
```

The agent navigates, searches, and extracts information, pausing when it needs your help with authentication, verification, or important decisions.

## Interactive mode

`browse.py` provides an interactive CLI for natural language browser automation. The agent works autonomously, showing real-time progress updates:

```
Step 1/25: Opening bbc.co.uk (1.2s)
Step 2/25: Navigating to News section (0.8s)
Step 3/25: Extracting top headlines (0.6s)
```

The agent pauses for human input only when necessary (authentication, CAPTCHA, ambiguous choices, or confirmation before actions like purchases). When the task completes, you'll see structured results and options to continue or exit.

### Keyboard shortcuts

During agent execution, a persistent footer pinned to the bottom of the terminal shows available shortcuts. B and Q respond immediately without waiting for the current agent step to finish:

| Key | Action |
|-----|--------|
| B | Toggle browser window visibility (hidden by default) |
| V | Toggle verbose mode on/off |
| F | Toggle vision mode (screenshot analysis for visually complex pages) |
| I | Send new instructions to the agent |
| P | Pause/resume agent execution |
| Q | Quit |

The browser starts hidden and auto-shows when authentication or CAPTCHA is needed. On macOS, hide/show uses osascript for instant response; other platforms use CDP window bounds.

### Intervention points

The agent requests human input in these situations:

**Security and verification:**
- **Authentication required** - Login pages or session timeouts (you log in manually in the browser)
- **CAPTCHA/verification** - Human verification challenges (you solve the CAPTCHA)

**Decision making:**
- **Ambiguous choice** - Multiple valid options where the agent cannot determine which to choose (you select from a numbered list)
- **Confirmation before action** - Destructive or significant actions like purchases, form submissions, or deletions (you confirm or cancel)
- **Confidence check** - When the agent is uncertain about a finding or next step, it pauses and asks you to decide

**Progress management:**
- **Agent stuck** - After 3 consecutive failures, the agent asks if you want to retry, get a page description, provide new instructions, or abort
- **Approaching max steps** - At 80% of the step limit, you can increase the limit, wrap up, or stop
- **Progress checkpoint** - At major phase transitions (e.g. searching to comparing), the agent shows a brief progress summary and asks whether to continue or adjust

**Planning:**
- **Batched upfront questions** - Before starting, the agent analyses your task for likely ambiguities and asks 0-3 clarifying questions up front to minimise interruptions
- **Sub-goal summary** - When a sub-goal completes, the agent shows a mini-summary and asks "what next?"

The terminal bell rings when the agent needs your attention (works with iTerm2 and most terminals).

See `docs/interaction-spec.md` for the complete UX specification.

## Multi-turn sessions

Sessions maintain context across tasks - follow-up tasks understand what happened before. After each task, the agent generates a concise summary that feeds into the next task's prompt, so you can build on prior results naturally.

```
> Find the top 3 wireless keyboards under £50 on Amazon UK

✓ Task completed in 9 steps (16.3s)

Found 3 wireless keyboards:
  1. Logitech K380 - £29.99
  2. Anker A7726 - £25.99
  3. iClever BK10 - £33.99

Session log saved to: logs/browse-session-20260216-143022.md

What would you like to do next?
  1. New task (with session context)
  2. View session log
  3. Exit

Choose [3]: 1

What would you like to do?
> Compare those top 2 and tell me which has better reviews
```

The agent remembers finding those keyboards and knows which two you mean.

### Output modes

- **Default** - Findings-only summary after each task
- **Verbose** - Full action log plus findings. Enable with `uv run python browse.py --verbose` or opt in at session start
- **JSON** - Structured output for piping to other tools: `uv run python run_task.py --json "your task"`

### Session logs

Session logs are auto-saved to `logs/` after each task completes. The path is shown in dim text below the results. Choose "View session log" from the completion menu to display the full summary. Exports include all task summaries, structured data, and a suggested follow-up prompt formatted for Claude Code.

## Setup

### Prerequisites

- Python 3.12+
- [UV](https://docs.astral.sh/uv/) package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli?WT.mc_id=AI-MVP-5004204) installed and logged in (`az login`)
- Azure subscription with access to deploy Microsoft Foundry (AI Services) resources
- **Platform**: Developed and tested on macOS with iTerm2. Linux should work with minor adjustments. Windows users will need WSL or Git Bash for the deployment scripts. Terminal bell notifications work best with iTerm2.

> **Cost note**: Running tasks costs roughly $0.01-0.05 per simple task using GPT-4.1-mini. See [Cost and capacity](#cost-and-capacity) for details.

### Installation

1. Clone the repository:

```bash
git clone https://github.com/Sealjay/foundry-browser-use.git
cd foundry-browser-use
```

2. Install Python dependencies:

```bash
uv sync
```

3. Install Chromium (used by Browser Use via CDP):

```bash
uv run playwright install chromium
```

### Deploy Azure infrastructure

Deploy a [Microsoft Foundry resource](https://learn.microsoft.com/azure/ai-foundry/openai/how-to/create-resource?WT.mc_id=AI-MVP-5004204) to `rg-browser-agent` in `uksouth`:

**Option A: Azure CLI deployment**

```bash
./infra/deploy.sh rg-browser-agent uksouth oai-foundry-browser
```

**Option B: [Bicep](https://learn.microsoft.com/azure/azure-resource-manager/bicep/overview?WT.mc_id=AI-MVP-5004204) deployment**

```bash
./infra/deploy-bicep.sh rg-browser-agent
```

Both scripts will output environment variable values - copy these to your `.env` file. When you're done, remember to [tear down](#teardown) these resources to avoid ongoing charges.

### Configure .env

Copy `.env.example` to `.env` and fill in your Microsoft Foundry credentials from the deployment output:

```bash
cp .env.example .env
# Edit .env with your Foundry endpoint, API key, and deployment name
```

> **Security note**: Never commit `.env` to version control (already in `.gitignore`). On shared machines, restrict permissions: `chmod 600 .env`.

## Usage

The interactive CLI (`browse.py`) is the recommended way to run browser automation tasks. For scripting or non-interactive use, you can also:

Run the example agent:

```bash
uv run python agent.py
```

Run a custom task programmatically:

```bash
uv run python run_task.py "go to google.com and search for cats"
```

## Configuration

The agent can be configured with the following parameters:

- `use_vision`: Set to `False` (default) for DOM-only mode, or `True` to include screenshots. DOM-only mode is significantly faster and more cost-effective.
- `max_steps`: Maximum number of steps the agent can take (default: 25 in interactive mode, 10 in scripting mode)
- `model`: Swap between different OpenAI models on Microsoft Foundry by changing `AZURE_OPENAI_DEPLOYMENT_NAME` in `.env`

When using the interactive CLI (`browse.py`), the agent starts with 25 steps and offers to increase the limit if needed.

See [Microsoft Foundry model documentation](https://learn.microsoft.com/azure/ai-foundry/openai/?WT.mc_id=AI-MVP-5004204) for available models and deployment guidance.

### Privacy and telemetry

> **Important**: The browser-use library sends anonymous usage data to PostHog by default. This project **disables telemetry** in `.env.example` because browser automation tasks can involve sensitive sites and workflows. Ensure `ANONYMIZED_TELEMETRY=false` is set in your `.env` file (already included in `.env.example`).

## Cost and capacity

Pricing is indicative only and subject to change. For current rates, see the [Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/?WT.mc_id=AI-MVP-5004204). As a rough guide (as of February 2025), GPT-4.1-mini costs approximately $0.40 per 1M input tokens and $1.60 per 1M output tokens. Actual costs vary based on task complexity, context size, and Azure region.

> **Tear down when idle**: Run `./infra/teardown.sh rg-browser-agent` when you're finished to stop all charges. The agent can consume quota quickly during multi-step tasks.

### TPM (tokens per minute)

The deployment scripts default to 150K [TPM](https://learn.microsoft.com/azure/ai-foundry/openai/how-to/quota?WT.mc_id=AI-MVP-5004204) (GlobalStandard SKU). Browser automation is token-heavy - each step sends DOM content plus conversation history, so a single task can consume 10-50K tokens. With multi-turn sessions the context grows further. If you hit rate limits (HTTP 429), increase your TPM allocation in the Azure portal or via the deployment scripts. The Azure CLI deployment accepts `--sku-capacity` and the Bicep template has a `skuCapacity` parameter.

## Teardown

To delete all Azure resources and avoid charges:

```bash
./infra/teardown.sh rg-browser-agent
```

**Warning:** This permanently deletes the resource group and all resources within it.

## Project structure

```
foundry-browser-use/
  browse.py                  # Interactive CLI entry point
  agent.py                   # Demo agent (scripting)
  run_task.py                # One-shot task runner (scripting)
  browser_agent/             # Interactive CLI package
    cli.py                   #   CLI orchestrator
    runner.py                #   Agent execution wrapper
    intervention.py          #   Human intervention handlers
    keyboard.py              #   Keyboard shortcuts, agent state, persistent footer
    display.py               #   Result formatting
    session.py               #   Multi-turn session context
  infra/                     # Azure deployment scripts
    deploy.sh                #   Azure CLI deployment
    deploy-bicep.sh          #   Bicep deployment
    main.bicep               #   Bicep template
    teardown.sh              #   Resource cleanup
  docs/
    interaction-spec.md      #   UX specification
```

## Limitations

- **DOM-only mode** works best on content-heavy and form-based sites. Modern SPAs with heavily obfuscated DOMs, Shadow DOM, or Canvas/WebGL rendering may not parse well. Press `F` during execution to toggle vision mode on, or set `use_vision=True` in code for visually complex pages (costs more tokens).
- **Anti-bot measures**: Many websites detect and block browser automation. The agent pauses for CAPTCHAs, but persistent blocking or account flagging is possible. Respect target sites' terms of service.
- **Platform**: Built and tested on macOS. Shell scripts, terminal features (bell, persistent footer), and browser window management (osascript on macOS, CDP on others) may behave differently on Linux or Windows/WSL.

## Contributing

Contributions are welcome via pull request.

## Licence

This project is licensed under the MIT Licence - see the [LICENCE](LICENCE) file for details.
