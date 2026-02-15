# foundry-browser-use

Interactive AI browser automation using Browser Use and Microsoft Foundry. Natural language browser agent with intelligent intervention points for authentication, verification, and confirmation. DOM-first Playwright agent powered by Azure OpenAI models for fast, low-cost web task automation.

## Quick start

```bash
uv run python browse.py
```

```
Browse - AI browser automation

What would you like to do?
> Go to amazon.co.uk and find the cheapest USB-C hub with at least 4 ports
```

The agent autonomously navigates, searches, and extracts information, pausing only when it needs your help with authentication, verification, or important decisions.

> First time? See [Setup](#setup) for installation and Azure deployment instructions.

## Interactive mode

`browse.py` provides an interactive CLI for natural language browser automation. The agent works autonomously, showing real-time progress updates:

```
Step 1/25: Opening amazon.co.uk (1.2s)
Step 2/25: Searching for 'USB-C hub 4 ports' (0.8s)
Step 3/25: Clicking 'Search' (0.6s)
```

The agent pauses for human input only when necessary (authentication, CAPTCHA, ambiguous choices, or confirmation before actions like purchases). When the task completes, you'll see structured results and options to continue or exit.

### Keyboard shortcuts

During agent execution, a status bar at the bottom of the terminal shows available shortcuts:

| Key | Action |
|-----|--------|
| B | Toggle browser window visibility (hidden by default) |
| V | Toggle verbose mode on/off |
| I | Send new instructions to the agent |
| P | Pause/resume agent execution |
| Q | Quit |

The browser starts hidden (headed but offscreen) and auto-shows when authentication or CAPTCHA is needed.

### Intervention points

The agent requests human input in these situations:

- **Authentication required** - Login pages or session timeouts (you log in manually in the browser)
- **CAPTCHA/verification** - Human verification challenges (you solve the CAPTCHA)
- **Ambiguous choice** - Multiple valid options where the agent cannot determine which to choose (you select from a numbered list)
- **Confirmation before action** - Destructive or significant actions like purchases, form submissions, or deletions (you confirm or cancel)
- **Agent stuck** - After 3 consecutive failures, the agent asks if you want to retry, get a page description, provide new instructions, or abort
- **Approaching max steps** - At 80% of the step limit, you can increase the limit, wrap up, or stop
- **Progress checkpoint** - At major phase transitions (e.g. searching to comparing), the agent shows a brief progress summary and asks whether to continue or adjust
- **Confidence check** - When the agent is uncertain about a finding or next step, it pauses and asks you to decide
- **Sub-goal summary** - When a sub-goal completes, the agent shows a mini-summary and asks "what next?"
- **Batched upfront questions** - Before starting, the agent analyses your task for likely ambiguities and asks 0-3 clarifying questions up front to minimise interruptions

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

What would you like to do next?
  1. New task (with session context)
  2. Export session summary
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

### Export

After any task, choose "Export session summary" to save a self-contained markdown file. The export includes all task summaries, structured data, and a suggested follow-up prompt formatted for Claude Code.

## Setup

### Prerequisites

- Python 3.12+
- UV package manager
- Azure CLI installed and logged in (`az login`)
- Azure subscription with OpenAI access

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

3. Install Chromium for Playwright:

```bash
uv run playwright install chromium
```

### Deploy Azure infrastructure

Deploy an Azure OpenAI resource to `rg-browser-agent` in `uksouth`:

**Option A: Azure CLI deployment**

```bash
./infra/deploy.sh rg-browser-agent uksouth oai-foundry-browser
```

**Option B: Bicep deployment**

```bash
./infra/deploy-bicep.sh rg-browser-agent
```

Both scripts will output environment variable values - copy these to your `.env` file.

### Configure .env

Copy `.env.example` to `.env` and fill in your Azure OpenAI credentials from the deployment output:

```bash
cp .env.example .env
# Edit .env with your Azure OpenAI endpoint, API key, and deployment name
```

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
- `model`: Swap between different Azure OpenAI models by changing `AZURE_OPENAI_DEPLOYMENT_NAME` in `.env`

When using the interactive CLI (`browse.py`), the agent starts with 25 steps and offers to increase the limit if needed.

See [Azure OpenAI documentation](https://learn.microsoft.com/azure/ai-foundry/openai/?WT.mc_id=AI-MVP-5004204) for available models and deployment guidance.

### Telemetry

The browser-use library sends anonymous usage data to PostHog by default. This project disables telemetry in `.env.example` because browser automation tasks can involve sensitive sites and workflows, and users should opt in to data collection rather than opt out. To disable telemetry, set `ANONYMIZED_TELEMETRY=false` in your `.env` file (already included in `.env.example`).

## Cost and capacity

GPT-4.1-mini pricing: ~$0.40 per 1M input tokens, ~$1.60 per 1M output tokens (~$0.77/hour or ~£0.57/hour). Remember to tear down your Azure resources when not in use to avoid ongoing costs.

### TPM (tokens per minute)

The deployment scripts default to 150K TPM (GlobalStandard SKU). Browser automation is token-heavy - each step sends DOM content plus conversation history, so a single task can consume 10-50K tokens. With multi-turn sessions the context grows further. If you hit rate limits (HTTP 429), increase your TPM allocation in the Azure portal or via the deployment scripts. The Azure CLI deployment accepts `--sku-capacity` and the Bicep template has a `skuCapacity` parameter.

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

## Contributing

Contributions are welcome via pull request.

## Licence

This project is licensed under the MIT Licence - see the [LICENCE](LICENCE) file for details.
