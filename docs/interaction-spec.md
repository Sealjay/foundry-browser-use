# Interaction Specification: browse.py

**Version:** 1.0
**Date:** 2026-02-15
**Target User:** Moderately technical (comfortable with terminal, not necessarily a developer)

---

## Overview

`browse.py` is an interactive CLI tool that allows users to describe browser automation tasks in natural language and watch an AI agent complete them. The agent works autonomously but pauses for human input when authentication, verification, or confirmation is required.

## Design Principles

1. **Progressive disclosure** - Show only what's needed at each step
2. **Favour autonomy over interruption** - Only pause when truly necessary
3. **Clear defaults** - Every prompt has a sensible default action
4. **Plain language** - Avoid technical jargon, DOM details, or API internals
5. **Consistent formatting** - Questions end with `?`, status lines don't
6. **British English throughout** - "colour" not "color", "authorisation" not "authorization"
7. **No emojis** - Keep output professional and terminal-friendly

---

## 1. Startup and Task Input

### Initial Greeting

On startup, show a brief one-line greeting followed by the task prompt:

```
Browse - AI browser automation

What would you like to do? (e.g. 'Go to amazon.co.uk and find the cheapest USB-C hub with at least 4 ports')
>
```

**Implementation notes:**
- No ASCII art, banners, or version numbers
- Cursor positioned immediately after `> ` for input
- Example should be concrete and practical (avoid abstract examples like "search for X")

### Task Confirmation

After the user enters a task, rephrase it to confirm understanding:

```
> Go to amazon.co.uk and find the cheapest USB-C hub with at least 4 ports

I'll search Amazon UK for USB-C hubs with 4+ ports and identify the lowest price.

Is this correct? [Y/n]:
```

**Refinement flow:**
- If user presses Enter or types `y`/`Y`, proceed
- If user types `n`/`N`, re-prompt: `What would you like to do instead?`
- Allow user to clarify or refine the task

### Environment Validation

Before starting the agent, validate Azure OpenAI configuration silently. Only show output if there's an error:

**Success case:**
```
Is this correct? [Y/n]: y
Starting agent...

Step 1/25: Opening amazon.co.uk
```

**Error case:**
```
Is this correct? [Y/n]: y

Configuration error: AZURE_OPENAI_API_KEY not found in environment.
Please set the required environment variables in .env or your shell.

See .env.example for the full list of required variables.
```

**Implementation notes:**
- No stack traces or Python exceptions
- Point user to `.env.example` for guidance
- Exit cleanly with status code 1

---

## 2. Agent Working - Live Status

### Status Line Format

Show a compact, updating status line for each agent step:

```
Step 3/25: Clicking 'Sort by price: low to high' (2.1s)
```

**Format breakdown:**
- `Step X/Y` - Current step and max steps
- Plain English description in single quotes for UI elements
- Elapsed time in parentheses (only if step takes >1 second)

### Visual Feedback

**Spinner for long operations:**
```
Step 4/25: Loading search results ⠋ (3.2s)
```

Use a simple spinner character (⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏) that cycles every 100ms for steps taking >2-3 seconds.

**Brief flash for quick steps:**

For steps completing in <1 second, show the line for at least 300ms before updating to the next step, so user sees progress rather than a blur.

### Colour Usage

Use colour sparingly and consistently:

- **Default (no colour)** - Normal progress
- **Yellow** - Warnings (approaching max steps, retrying after failure)
- **Green** - Success (task completed)
- **Red** - Errors (unrecoverable failures)

**Example with warning:**
```
Step 21/25: Clicking 'Add to basket' (1.3s)
⚠ Approaching step limit (21/25). Agent will prompt for guidance at step 24.
```

### What NOT to Show

Do not display:
- Raw DOM snippets or HTML
- CSS selectors (e.g., `button.a-button-primary`)
- Token counts or API usage
- HTTP status codes
- Python log levels (DEBUG, INFO, etc.)
- Model reasoning or internal agent state

---

## 3. Human Intervention Points

### 3.1 Authentication Required

**Scenario:** Agent detects a login page or session timeout.

**Prompt:**
```
Step 7/25: Detected login page

The site requires authentication. Please log in manually in the browser window.
Press Enter when you've logged in to continue...
```

**Implementation notes:**
- Pause agent execution
- Ensure browser window is visible and focused
- Wait for Enter key press
- Resume from next step
- If login fails (still on login page after 2 retries), treat as "agent stuck" scenario

### 3.2 CAPTCHA/Verification

**Scenario:** Agent detects CAPTCHA, reCAPTCHA, or human verification challenge.

**Prompt:**
```
Step 11/25: CAPTCHA detected

Please solve the CAPTCHA in the browser window.
Press Enter when you've completed it...
```

**Implementation notes:**
- Pause agent execution
- Bring browser window to foreground
- Wait for Enter key press
- Resume and verify CAPTCHA was solved
- If CAPTCHA persists after 2 attempts, offer to abort or retry

### 3.3 Ambiguous Choice

**Scenario:** Agent identifies multiple valid options (e.g., multiple products, links, or actions) and cannot determine which to choose.

**Prompt:**
```
Step 9/25: Found multiple USB-C hubs

I found 5 hubs that match your criteria:

  1. Anker 547 USB-C Hub (7-in-1) - £34.99
  2. UGREEN USB C Hub 4 Ports - £15.99 ⭐ Cheapest
  3. Belkin USB-C Hub (4-Port) - £29.99
  4. Cable Matters 201053 USB-C Hub - £18.49
  5. Hiearcool USB C Hub 7 in 1 - £16.99
  6. None of these - let me refine the search

Which would you like? [2]:
```

**Implementation notes:**
- Present maximum 5 options (if more, show top 5 by relevance)
- Always include "None of these" as the last option
- Highlight recommended choice with marker (⭐) if applicable
- Default to the recommended choice in square brackets `[2]`
- If user presses Enter, use default
- If user types a number, select that option
- If user types `6` or "none", ask: `How would you like to refine the search?`

### 3.4 Confirmation Before Action

**Scenario:** Agent is about to perform a destructive, irreversible, or significant action (e.g., purchase, delete, send message, post publicly).

**Prompt:**
```
Step 15/25: Ready to add item to basket

I'm about to add this item to your basket:
  Product: UGREEN USB C Hub 4 Ports
  Price: £15.99
  Quantity: 1

Proceed? [y/N]:
```

**Implementation notes:**
- Default to `N` (safe option) for destructive actions
- Show clear summary of what will happen
- If user types `n`/`N` or presses Enter, abort and ask: `What would you like to do instead?`
- If user types `y`/`Y`, proceed with action

**Actions requiring confirmation:**
- Adding items to cart/basket
- Submitting forms with personal data
- Making purchases or payments
- Posting, publishing, or sending messages
- Deleting or removing items
- Changing account settings

### 3.5 Agent Stuck

**Scenario:** Agent fails the same step 3 consecutive times or cannot determine next action.

**Prompt:**
```
Step 12/25: Unable to proceed

I tried to click the 'Next page' button but couldn't find it on the page.
This might mean:
  - The page layout has changed
  - The element is hidden or not yet loaded
  - I'm looking in the wrong place

What would you like to do?
  1. Retry (I'll try again)
  2. Describe what you see (I'll tell you what's on the page)
  3. Give me new instructions
  4. Abort task

Choose [1]:
```

**Implementation notes:**
- Explain the problem in plain English
- Offer 4 clear options with sensible default (retry)
- If user chooses option 2, show simplified page structure (headings, buttons, links - no DOM details)
- If user chooses option 3, prompt: `What should I do instead?` and treat as new task continuation
- If user chooses option 4, skip to completion summary with partial results

### 3.6 Max Steps Approaching

**Scenario:** Agent reaches 80% of max_steps (default 25, so triggers at step 20).

**Prompt:**
```
Step 20/25: Sorting results by price

⚠ Approaching step limit (20/25 steps used).

What would you like to do?
  1. Continue (increase limit to 50 steps)
  2. Wrap up and show results so far
  3. Stop now

Choose [1]:
```

**Implementation notes:**
- Trigger at 80% of max_steps
- Option 1 doubles the step limit (25 → 50, or 50 → 100)
- Option 2 tells agent to complete current action and summarise
- Option 3 stops immediately and shows partial results
- Default to option 1 (continue) - user explicitly requested a task

### 3.7 Progress Checkpoint

**Scenario:** Agent detects a major phase transition in its `next_goal` - for example, moving from searching to comparing results, or from reading content to submitting a form.

**Prompt:**
```
Step 10/25: Phase transition - searching → comparing

Progress so far:
  Found 5 USB-C hubs matching your criteria on Amazon UK.

Continue with the comparison, or would you like to adjust?
  1. Continue
  2. Adjust instructions

Choose [1]:
```

**Implementation notes:**
- Triggered by phase-transition detection in `next_goal` (e.g. searching to comparing, reading to submitting)
- Shows a brief summary of what has been accomplished so far
- Default to option 1 (continue)
- If user chooses option 2, prompt: `What should I do differently?`

### 3.8 Confidence Check

**Scenario:** The LLM's evaluation contains hedging language ("unsure", "might", "could be", "not certain"), indicating low confidence in a finding or next step.

**Prompt:**
```
Step 14/25: Uncertain about next step

I found a price of £15.99 but I'm not certain this includes VAT - the listing
is ambiguous.

How would you like to proceed?
  1. Continue with this assumption
  2. Let me check manually in the browser
  3. Give me new instructions

Choose [1]:
```

**Implementation notes:**
- Triggered when LLM evaluation contains hedging language
- Shows what the agent is uncertain about and why
- Default to option 1 (continue with current assumption)
- Option 2 pauses for the user to inspect the browser window, then press Enter to resume
- Option 3 prompts: `What should I do instead?`

### 3.9 Sub-goal Summary

**Scenario:** The LLM's evaluation indicates a sub-goal has been completed (e.g. "finished extracting product details, now need to compare prices").

**Prompt:**
```
Step 12/25: Sub-goal completed

I've finished gathering product details for all 5 USB-C hubs.

What would you like to do next?
  1. Continue to the next step (compare prices)
  2. Show me what you've found so far
  3. Give me new instructions

Choose [1]:
```

**Implementation notes:**
- Triggered when LLM evaluation indicates a sub-goal is done
- Shows a mini-summary of what was accomplished
- Suggests the logical next step in option 1
- Option 2 displays current findings without ending the task
- Default to option 1 (continue)

### 3.10 Batched Upfront Questions

**Scenario:** Before the agent starts working, an LLM call analyses the task for likely ambiguities and generates 0-3 clarifying questions. If no ambiguities are detected, the agent starts immediately without interruption.

**Prompt:**
```
Before I start, a couple of quick questions:

  1. Are you looking for hubs with USB-A ports, USB-C ports, or a mix of both?
     > A mix of both

  2. Should I include hubs that are currently out of stock?
     > No, in-stock only

Thanks - starting now.
Starting agent...

Step 1/25: Opening amazon.co.uk (1.2s)
```

**Implementation notes:**
- One LLM call before agent execution analyses the task for ambiguities
- Generates 0-3 questions (if 0, agent starts immediately - no prompt shown)
- Questions shown in a numbered list; user answers each in sequence
- Answers are appended to the task prompt as additional context
- Keeps interruptions minimal by front-loading all clarification

### Terminal bell

All intervention prompts (3.1-3.10) ring the terminal bell (`\a`) to alert the user that the agent needs attention. This works with iTerm2 and most terminal emulators.

---

## 4. Keyboard Shortcuts

During agent execution, a persistent status bar at the bottom of the terminal shows available keyboard shortcuts. The status bar updates dynamically to reflect the current state (e.g., "Browser: visible" after pressing B).

### Terminal layout during execution

```
Step 3/25: Searching for 'USB-C hub' (1.2s)       <- Rich output (scrolls)
Step 4/25: Loading results (2.1s)

[B] Browser: hidden  [V] Verbose: off  [I] Instruct  [P] Pause  [Q] Quit
```

The status bar sits at the bottom of the terminal. Agent step output scrolls above it. The bar re-renders on each keypress to reflect the current state.

### Key reference

| Key | Action | Behaviour on press |
|-----|--------|--------------------|
| B | Toggle browser visibility | Toggles the browser window between visible and hidden. The window starts offscreen (headed but positioned at -9999, -9999) and is moved to (100, 100) when shown. When hidden again, it moves back offscreen. |
| V | Toggle verbose mode | Switches verbose output on or off mid-run. When toggled on, the agent shows full action details for each step. A confirmation line is printed (e.g., "Verbose: on"). |
| I | Send new instructions | Pauses execution and opens a text prompt for the user to type new instructions. The instructions are queued and injected into the next agent step's context prompt. Execution resumes automatically after the user submits. |
| P | Pause/resume | Pauses agent execution after the current step completes. Press P again to resume. While paused, a "Paused" indicator appears in the status bar. |
| Q | Quit | Requests the agent to stop. Execution halts and partial results are shown. |

### Browser window management

The browser starts hidden by default - Chromium launches in headed mode but positioned offscreen so the window is not visible. This keeps the terminal experience clean while still allowing full browser interaction when needed.

When an intervention requiring the browser fires (authentication or CAPTCHA - see sections 3.1 and 3.2), the browser window is automatically moved onscreen and the terminal bell rings. After the intervention resolves, the window moves back offscreen unless the user has manually toggled it visible with B.

### When shortcuts are active

Keyboard shortcuts are only active during agent execution (while steps are running). They are not active during:

- Task input prompts (the initial "What would you like to do?" prompt)
- Intervention prompts (numbered choice menus, confirmation prompts)
- Post-task menus (the "What would you like to do next?" options)

During these prompts, normal text input and number selection work as described in their respective sections.

---

## 5. Completion

### Success Summary

**Format:**
```
✓ Task completed in 18 steps (34.2s)

Results:
  Product: UGREEN USB C Hub 4 Ports
  Price: £15.99
  Link: https://www.amazon.co.uk/dp/B0EXAMPLE

What would you like to do next?
  1. New task (with session context)
  2. Export session summary
  3. Exit

Choose [3]:
```

**Implementation notes:**
- Green checkmark (✓) for successful completion
- Total steps and elapsed time (NOT token cost or API usage)
- Structured data in consistent format (product details, links, etc.)
- Narrative results as plain text paragraphs
- Option 1 starts a new task with prior session context carried forward
- Option 2 exports a self-contained markdown summary (see section 7)
- Option 3 exits the session
- Default to exit (option 3)

### Partial Completion

**Format:**
```
⚠ Task partially completed (stopped at step 12/25)

I found several USB-C hubs but couldn't determine the absolute cheapest due to dynamic pricing and sale badges. Here are the top 3:

  1. UGREEN USB C Hub 4 Ports - £15.99
  2. Hiearcool USB C Hub 7 in 1 - £16.99
  3. Cable Matters 201053 USB-C Hub - £18.49

What would you like to do next?
  1. Refine the search
  2. New task (with session context)
  3. Export session summary
  4. Exit

Choose [4]:
```

**Implementation notes:**
- Yellow warning symbol (⚠) for partial completion
- Explain why task wasn't fully completed
- Show what was accomplished
- Option 1 continues with the current task, allowing the user to refine
- Option 2 starts a new task with prior session context carried forward
- Option 3 exports a self-contained markdown summary (see section 7)
- Option 4 exits the session
- Default to exit (option 4)

### Table Format for Structured Data

When presenting multiple items or structured data, use ASCII tables:

```
✓ Task completed in 22 steps (41.5s)

Found 3 USB-C hubs under £20:

┌─────────────────────────────────┬─────────┬─────────┐
│ Product                         │ Price   │ Ports   │
├─────────────────────────────────┼─────────┼─────────┤
│ UGREEN USB C Hub                │ £15.99  │ 4       │
│ Hiearcool USB C Hub 7 in 1      │ £16.99  │ 7       │
│ Cable Matters 201053            │ £18.49  │ 4       │
└─────────────────────────────────┴─────────┴─────────┘

Cheapest option: UGREEN USB C Hub at £15.99
Link: https://www.amazon.co.uk/dp/B0EXAMPLE
```

**Implementation notes:**
- Use box-drawing characters for clean tables
- Keep column widths reasonable (truncate long text with ellipsis)
- Maximum 5 rows (if more results, show top 5 and note "showing 5 of 12 results")
- Always include a summary line below the table

---

## 6. Error Handling

### Network Errors

**Scenario:** DNS failure, connection timeout, or network unreachable.

**Handling:**
```
Step 5/25: Opening amazon.co.uk
Network error: Unable to reach amazon.co.uk

Retrying (attempt 1 of 3)...
Step 5/25: Opening amazon.co.uk (2.1s)
```

**Implementation notes:**
- Auto-retry up to 3 times with exponential backoff (2s, 4s, 8s)
- Show retry attempt number
- After 3 failures, show final error:
  ```
  Network error: Unable to reach amazon.co.uk after 3 attempts.
  Please check your internet connection and try again.
  ```
- Exit cleanly with status code 1

### Azure OpenAI API Errors

**Scenario:** Rate limit, quota exceeded, authentication failure, model deployment error.

**Handling:**
```
API error: Rate limit exceeded. Your Azure OpenAI deployment is receiving too many requests.

Please wait a moment and try again, or check your Azure quota settings.
```

**Implementation notes:**
- Translate HTTP errors to friendly messages:
  - 401/403 → "Authentication failed. Please check your AZURE_OPENAI_API_KEY."
  - 429 → "Rate limit exceeded. Please wait and try again."
  - 500/502/503 → "Azure OpenAI service is temporarily unavailable. Please try again in a few moments."
  - 404 (deployment) → "Model deployment 'X' not found. Please check your AZURE_OPENAI_DEPLOYMENT_NAME."
- Never show raw HTTP status codes, JSON error bodies, or stack traces
- Exit cleanly with status code 1

### Browser Crashes

**Scenario:** Playwright browser process crashes or becomes unresponsive.

**Handling:**
```
Step 8/25: Clicking 'Search'

Browser crashed unexpectedly. Restarting browser...

Step 8/25: Clicking 'Search' (1.9s)
```

**Implementation notes:**
- Auto-restart browser process
- Resume from the failed step
- If browser crashes 3 times in a row, show error:
  ```
  Browser keeps crashing. This might be due to:
    - Insufficient memory
    - Incompatible browser version
    - Website incompatibility

  Please try again later or choose a different task.
  ```
- Exit cleanly with status code 1

### Unhandled Exceptions

**Scenario:** Any Python exception not caught by specific handlers above.

**Handling:**
```
An unexpected error occurred. This has been logged for debugging.

If this persists, please report it as an issue:
https://github.com/Sealjay/foundry-browser-use/issues
```

**Implementation notes:**
- Never show Python tracebacks to users
- Log full traceback to a file (e.g., `~/.foundry-browser-use/logs/error-YYYYMMDD-HHMMSS.log`)
- Mention log location: `Error details saved to: <path>`
- Exit cleanly with status code 1

---

## 7. Multi-turn Sessions

### Overview

Sessions maintain context across tasks. After each task completes, the LLM generates a concise summary. That summary - not raw history - is injected into the next task's prompt, so follow-up tasks understand prior results.

### Session Context Flow

1. User enters a task
2. `Session.build_context_prompt()` generates context from prior task summaries
3. Agent prompt becomes: `"{context}\n\nNew task: {user_task}"`
4. Agent runs with awareness of prior tasks
5. On completion, an additional LLM call generates a concise summary
6. `TaskRecord` is appended to the session

**Context cap:** If 10 or more tasks have been completed, only the last 5 summaries are included in full; earlier ones are condensed to a single line each.

### Example: Two-task Session

```
Browse - AI browser automation

What would you like to do?
> Find the top 3 wireless keyboards under £50 on Amazon UK

I'll search Amazon UK for wireless keyboards under £50 and identify the top 3.

Is this correct? [Y/n]: y
Starting agent...

Step 1/25: Opening amazon.co.uk (1.1s)
Step 2/25: Searching for 'wireless keyboard' (0.7s)
Step 3/25: Clicking 'Search' (0.5s)
Step 4/25: Setting price filter to under £50 (1.3s)
Step 5/25: Sorting by average customer review (0.9s)
Step 6/25: Extracting top results (2.1s)

✓ Task completed in 6 steps (6.6s)

Found 3 wireless keyboards under £50:
  1. Logitech K380 - £29.99 (4.7 stars)
  2. Anker A7726 Ultra-Slim - £25.99 (4.5 stars)
  3. iClever BK10 - £33.99 (4.4 stars)

What would you like to do next?
  1. New task (with session context)
  2. Export session summary
  3. Exit

Choose [3]: 1

What would you like to do?
> Compare those top 2 and tell me which has better battery life

I'll compare the Logitech K380 and Anker A7726 and check their battery life specs.

Is this correct? [Y/n]: y
Starting agent...

Step 1/25: Opening Logitech K380 product page (1.4s)
Step 2/25: Extracting battery specifications (1.1s)
Step 3/25: Opening Anker A7726 product page (1.2s)
Step 4/25: Extracting battery specifications (0.9s)
Step 5/25: Comparing results (0.6s)

✓ Task completed in 5 steps (5.2s)

Battery life comparison:
  Logitech K380: Up to 2 years (2x AAA batteries)
  Anker A7726: Up to 6 months (built-in rechargeable)

The Logitech K380 has significantly longer battery life, though it uses
replaceable batteries rather than a rechargeable cell.

What would you like to do next?
  1. New task (with session context)
  2. Export session summary
  3. Exit

Choose [3]:
```

The agent understood "those top 2" because the first task's summary was injected into the second task's prompt.

### Output Modes

**Default (interactive):** Findings-only summary after each task. The completion block shows the summary and structured data.

**Verbose (`--verbose` flag or opt-in at session start):** Actions plus findings. Each step is shown during execution (as normal), and the full actions log is also included in the completion summary.

**Structured (`--json` flag, non-interactive):** For `run_task.py` only. Outputs JSON to stdout with `summary`, `structured_data`, `steps`, `elapsed`, and `success` fields. Designed for piping to other tools.

```bash
uv run python run_task.py --json "find cheapest USB-C hub on Amazon UK" | jq '.structured_data.price'
```

### Export Format

Choosing "Export session summary" from the completion menu writes a self-contained markdown file to `./browse-session-YYYYMMDD-HHMMSS.md`.

The export contains:
- A heading with the session date and number of tasks
- Each task's original prompt, summary, and structured data
- A suggested follow-up prompt formatted for Claude Code

**Example export:**

```markdown
# Browse session - 2026-02-15

## Task 1: Find the top 3 wireless keyboards under £50 on Amazon UK

**Summary:** Found 3 wireless keyboards under £50 on Amazon UK, sorted by review rating.

**Data:**
- Logitech K380: £29.99 (4.7 stars)
- Anker A7726 Ultra-Slim: £25.99 (4.5 stars)
- iClever BK10: £33.99 (4.4 stars)

## Task 2: Compare those top 2 and tell me which has better battery life

**Summary:** Compared Logitech K380 and Anker A7726 battery life. K380 lasts up to 2 years
(replaceable AAA batteries); A7726 lasts up to 6 months (rechargeable).

**Suggested follow-up:** Based on these findings, you could ask Claude Code to draft a
comparison table or purchase recommendation.
```

---

## 8. General UX Principles

### Input and Defaults

1. **Every prompt has a clear default** - shown in square brackets `[Y/n]`, `[2]`
2. **Press Enter to accept default** - no need to type `y` if that's the default
3. **Case-insensitive input** - `Y`, `y`, `yes`, `Yes` all work
4. **Number selection** - type just the number, no need for extra characters

### Formatting Standards

1. **Questions end with `?`** - e.g., "Is this correct?"
2. **Status lines don't** - e.g., "Step 3/25: Clicking 'Search'"
3. **UI elements in single quotes** - e.g., 'Add to basket', 'Sort by price'
4. **Code/technical terms in backticks** - e.g., `browse.py`, `.env`
5. **Emphasis with bold** - e.g., **not** recommended
6. **URLs in plain text** - no markdown, just raw URLs

### Progressive Disclosure

1. **Start minimal** - one-line greeting, task prompt
2. **Reveal complexity gradually** - only show options when needed
3. **Hide technical details** - DOM, selectors, tokens, model reasoning
4. **Summarise, don't dump** - tables over raw lists, summaries over full text

### Consistency

1. **Use the same phrasing** - "What would you like to do next?" always the same
2. **Predictable options** - numbered lists, clear defaults
3. **Consistent symbols** - ✓ for success, ⚠ for warning, ✗ for error
4. **British English everywhere** - colour, authorisation, summarise, analyse

### Colour and Symbols

1. **Colour is optional** - tool works in terminals without colour support
2. **Symbols are universal** - ✓ ⚠ ✗ work everywhere
3. **Yellow for warnings** - approaching limits, retries
4. **Green for success** - task completed
5. **Red for errors** - unrecoverable failures
6. **Default (no colour) for progress** - normal operation

### Autonomy vs. Interruption

Pause for human input **only** when:
- Authentication required (login pages)
- CAPTCHA or human verification
- Ambiguous choice with multiple valid options
- Confirmation needed before destructive action
- Agent stuck after 3 failed attempts
- Approaching max steps limit

**Do NOT pause for:**
- Routine navigation
- Clicking buttons or links
- Extracting data
- Scrolling or searching
- Waiting for page load
- Minor errors that can be auto-retried

---

## Appendix: Example Session

**Full interaction example - multi-turn session with intervention:**

```
Browse - AI browser automation

What would you like to do? (e.g. 'Go to amazon.co.uk and find the cheapest USB-C hub with at least 4 ports')
> Find the cheapest USB-C hub with at least 4 ports on Amazon UK

Before I start, a quick question:

  1. Should I include third-party marketplace sellers, or only items sold by Amazon?
     > Either is fine

Thanks - starting now.

I'll search Amazon UK for USB-C hubs with 4+ ports and identify the lowest price.

Is this correct? [Y/n]: y
Starting agent...

Step 1/25: Opening amazon.co.uk (1.2s)
Step 2/25: Searching for 'USB-C hub 4 ports' (0.8s)
Step 3/25: Clicking 'Search' (0.6s)
Step 4/25: Loading search results ⠋ (3.4s)
Step 5/25: Clicking 'Sort by: Price: low to high' (1.1s)
Step 6/25: Waiting for sorted results (2.3s)
Step 7/25: Extracting product details (1.8s)

Step 7/25: Sub-goal completed

I've finished gathering the sorted product list.

What would you like to do next?
  1. Continue to the next step (identify cheapest with 4+ ports)
  2. Show me what you've found so far
  3. Give me new instructions

Choose [1]: 1

Step 8/25: Filtering for hubs with 4+ ports (0.9s)
Step 9/25: Verifying port counts on product pages (2.4s)

✓ Task completed in 9 steps (14.5s)

Found cheapest USB-C hub:

  Product: UGREEN USB C Hub 4 Ports
  Price: £15.99
  Ports: 4x USB 3.0
  Rating: 4.5 stars (2,847 reviews)
  Link: https://www.amazon.co.uk/dp/B0EXAMPLE

Runner-up:
  Product: Hiearcool USB C Hub 7 in 1
  Price: £16.99
  Ports: 4x USB 3.0 + 3 other
  Rating: 4.3 stars (1,204 reviews)

What would you like to do next?
  1. New task (with session context)
  2. Export session summary
  3. Exit

Choose [3]: 1

What would you like to do?
> Compare those two and check which one has better build quality reviews

I'll compare the UGREEN and Hiearcool hubs, focusing on review comments about
build quality.

Is this correct? [Y/n]: y
Starting agent...

Step 1/25: Opening UGREEN product page (1.3s)
Step 2/25: Reading build quality reviews (2.1s)
Step 3/25: Opening Hiearcool product page (1.1s)
Step 4/25: Reading build quality reviews (1.9s)
Step 5/25: Comparing findings (0.7s)

✓ Task completed in 5 steps (7.1s)

Build quality comparison:

┌──────────────────────────┬────────────────────────────────────────┐
│ Hub                      │ Build quality feedback                 │
├──────────────────────────┼────────────────────────────────────────┤
│ UGREEN USB C Hub         │ Solid aluminium body, well-reviewed    │
│ Hiearcool USB C Hub      │ Plastic body, some reports of flex     │
└──────────────────────────┴────────────────────────────────────────┘

Reviewers consistently rate the UGREEN hub higher for build quality. The
aluminium casing and thicker cable are frequently praised.

What would you like to do next?
  1. New task (with session context)
  2. Export session summary
  3. Exit

Choose [3]: 2

Session summary exported to: ./browse-session-20260215-143022.md

What would you like to do next?
  1. New task (with session context)
  2. Exit

Choose [2]: 2

Goodbye!
```

---

**End of specification**
