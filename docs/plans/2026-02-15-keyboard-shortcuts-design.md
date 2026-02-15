# Keyboard shortcuts and QoL improvements design

**Date:** 2026-02-15
**Status:** Approved

## Problem

The CLI is a passive experience during agent execution - the user watches step output scroll by with no way to interact until an intervention fires or the task completes. The browser window is always visible even when not needed. There is no way to adjust behaviour (verbose, instructions) mid-run.

## Goals

1. Persistent status bar showing keyboard shortcuts during agent execution
2. Single-keypress controls: toggle browser visibility, verbose mode, send instructions, pause, quit
3. Browser window hidden by default (headed but offscreen), auto-shown on intervention
4. Instructions injected into the next step without interrupting the current one
5. Dynamic verbose toggle mid-run

## Approach: prompt_toolkit with Rich output

Use prompt_toolkit for terminal input ownership (key bindings, bottom toolbar, async prompts). Rich output scrolls above the prompt via `patch_stdout()`. This mirrors how Claude Code uses Ink - a framework that owns the terminal rendering pipeline.

### Why prompt_toolkit

- Native asyncio support (`prompt_async()`, async key binding handlers)
- Bottom toolbar re-renders automatically on each keypress
- `patch_stdout()` lets Rich console output coexist cleanly
- Handles raw terminal mode, cleanup, and edge cases (resize, etc.)
- Well-maintained (3.0.52, August 2025), no display conflicts with Rich when used correctly

## Architecture

### New module: `browser_agent/keyboard.py`

**`AgentState`** dataclass (shared mutable state):
- `browser_visible: bool = False` - browser window toggle
- `verbose: bool` - verbose output toggle (initialised from session)
- `paused: bool = False` - pause flag
- `pending_instruction: str | None = None` - queued user instruction for next step
- `quit_requested: bool = False`
- `running: bool = False` - whether agent is currently executing

**`KeyHandler`** class:
- Holds `AgentState` reference and Rich `Console`
- `handle_key(key)` dispatches single keypresses:
  - `b` - toggle `browser_visible`, call browser show/hide
  - `v` - toggle `verbose`, print confirmation
  - `i` - set `paused=True`, prompt for instruction via prompt_toolkit, store in `pending_instruction`, unpause
  - `p` - toggle `paused`
  - `q` - set `quit_requested=True`
- `show_browser()` / `hide_browser()` - move Playwright window onscreen/offscreen via CDP

**`build_toolbar(state: AgentState)`** function:
- Returns prompt_toolkit `HTML` formatted text
- Shows: `[B] Browser: hidden  [V] Verbose: off  [I] Instruct  [P] Pause  [Q] Quit`
- Updates dynamically based on state values

### Browser window management

- Launch Chromium with `args=["--window-position=-9999,-9999"]` to start offscreen (headed but not visible)
- On `[B]` press: `page.evaluate("window.moveTo(100, 100)")` to show, `window.moveTo(-9999, -9999)` to hide
- On intervention (auth, CAPTCHA): auto-set `state.browser_visible = True` and move window onscreen, ring terminal bell
- After intervention resolves: move back offscreen unless user toggled it manually

### Step callback integration (runner.py)

Between steps, the callback checks `AgentState` flags in order:
1. `quit_requested` - raise `KeyboardInterrupt`
2. `paused` - `await asyncio.sleep(0.1)` loop until unpaused
3. `pending_instruction` - append to next step context prompt, clear the field
4. `verbose` - sync to `session.verbose` if changed

### CLI integration (cli.py)

- Create `AgentState` at session start, sync `verbose` from session
- Replace `rich.prompt.Prompt.ask()` / `Confirm.ask()` with `PromptSession.prompt_async()` for task input
- Keep Rich `Console` for all output formatting
- Wrap main loop in `patch_stdout()` context manager
- During agent execution: run key listener as concurrent asyncio task
- After agent execution: stop key listener, return to normal prompt mode

### Terminal layout during execution

```
Step 3/25: Searching for 'USB-C hub' (1.2s)       <- Rich output (scrolls)
Step 4/25: Loading results (2.1s)

[B] Browser: hidden  [V] Verbose: off  [I] Instruct  [P] Pause  [Q] Quit
```

## File changes

**New dependency:**
- `prompt-toolkit>=3.0.50` in `pyproject.toml`

**Create:**
- `browser_agent/keyboard.py` - AgentState, KeyHandler, build_toolbar()

**Modify:**
- `browser_agent/cli.py` - prompt_toolkit PromptSession, patch_stdout, key listener task
- `browser_agent/runner.py` - AgentState flag checks in step callback, browser window positioning, --window-position arg
- `browser_agent/intervention.py` - Auto-show browser on auth/CAPTCHA, set state.browser_visible
- `browser_agent/display.py` - Respect dynamic verbose from AgentState
- `README.md` - Document keyboard shortcuts section
- `docs/interaction-spec.md` - Add keyboard shortcut section with key reference table
