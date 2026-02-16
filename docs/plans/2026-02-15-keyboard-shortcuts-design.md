# Keyboard shortcuts and QoL improvements design

**Date:** 2026-02-15
**Status:** Implemented

## Problem

The CLI is a passive experience during agent execution - the user watches step output scroll by with no way to interact until an intervention fires or the task completes. The browser window is always visible even when not needed. There is no way to adjust behaviour (verbose, instructions) mid-run.

## Goals

1. Persistent status bar showing keyboard shortcuts during agent execution
2. Single-keypress controls: toggle browser visibility, verbose mode, send instructions, pause, quit
3. Browser window minimised by default, auto-shown on intervention
4. Instructions injected into the next step without interrupting the current one
5. Dynamic verbose toggle mid-run

## Approach: prompt_toolkit with Rich output

Use prompt_toolkit for terminal input ownership (key bindings, bottom toolbar, async prompts). Rich output scrolls above the prompt via `patch_stdout()`. This mirrors how Claude Code uses Ink - a framework that owns the terminal rendering pipeline.

### Why prompt_toolkit

- Native asyncio support (`prompt_async()`, async key binding handlers)
- `patch_stdout()` lets Rich console output coexist cleanly
- Handles raw terminal mode, cleanup, and edge cases (resize, etc.)
- Well-maintained (3.0.52, August 2025), no display conflicts with Rich when used correctly

**Note on bottom toolbar:** prompt_toolkit's `bottom_toolbar` only renders during active `prompt_async()` calls. During agent execution, the key listener runs in raw mode (not `prompt_async`), so the toolbar is not visible. Instead, a condensed shortcuts line is printed after each step in the step callback. The `build_toolbar` function remains for when the prompt is active between tasks.

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
  - `b` - toggle `browser_visible` (CDP minimize/restore handled by runner.py step callback)
  - `v` - toggle `verbose`, print confirmation
  - `i` - set `paused=True`, prompt for instruction via prompt_toolkit, store in `pending_instruction`, unpause
  - `p` - toggle `paused`
  - `q` - set `quit_requested=True`

**`build_toolbar(state: AgentState)`** function:
- Returns prompt_toolkit `HTML` formatted text for the bottom toolbar
- Uses action-based labels: `[B] Show browser`, `[V] More detail`, `[I] Instruct`, `[P] Pause`, `[Q] Quit`
- Labels change based on current state (e.g. "Minimise browser" when visible, "Show browser" when hidden)
- Only visible during `prompt_async()` calls (task input), not during agent execution

### Browser window management

**Approach:** CDP (Chrome DevTools Protocol) minimize/restore via `Browser.getWindowForTarget` and `Browser.setWindowBounds`.

**What didn't work:**
- `--window-position=-9999,-9999` - macOS clamps window coordinates, preventing offscreen placement
- `window.moveTo()` via `page.evaluate()` - modern browsers restrict this to same-origin contexts and macOS additionally clamps coordinates
- `--start-minimized` - not a recognised Chromium flag on macOS

**What works:**
- CDP `Browser.setWindowBounds({"windowId": id, "bounds": {"windowState": "minimized"}})` minimises the window reliably on macOS
- CDP `Browser.setWindowBounds({"windowId": id, "bounds": {"windowState": "normal"}})` restores it

**Lifecycle:**
1. Agent creates Chromium with `window_position=None` (prevents default `--window-position=0,0`)
2. Before `agent.run()`, call `agent.browser_session.start()` (idempotent - safe to call before `run()`)
3. Immediately call `_minimize_browser()` via CDP - browser is minimised before any steps execute
4. On `[B]` press: step callback detects `browser_visible` state change, calls `_restore_browser()` or `_minimize_browser()`
5. On intervention (auth, CAPTCHA): `intervention.py` sets `state.browser_visible = True`, step callback restores window
6. Window ID is cached after first CDP lookup (`_browser_window_id`)

**Key implementation detail:** `agent.browser_session.start()` is idempotent. Calling it before `agent.run()` pre-connects the browser and CDP client, making the minimize call possible immediately. When `agent.run()` calls `start()` again internally, it's a no-op.

### Step callback integration (runner.py)

Between steps, the callback checks `AgentState` flags in order:
1. `quit_requested` - raise `KeyboardInterrupt`
2. `paused` - `await asyncio.sleep(0.1)` loop until unpaused
3. `pending_instruction` - append to next step context prompt, clear the field
4. `verbose` - sync to `session.verbose` if changed
5. `browser_visible` changed - toggle CDP minimize/restore

After state checks, the callback:
- Prints the step status line (e.g. `Step 3/25: Searching for 'USB-C hub' (1.2s)`)
- Prints an action-based shortcuts reminder in cyan (e.g. `[B] Show browser  [V] More detail  [I] Instruct  [P] Pause  [Q] Quit`)

### CLI integration (cli.py)

- Create `AgentState` at session start, sync `verbose` from session
- Replace `rich.prompt.Prompt.ask()` / `Confirm.ask()` with `PromptSession.prompt_async()` for task input
- Keep Rich `Console` for all output formatting
- Wrap main loop in `patch_stdout()` context manager
- During agent execution: run key listener as concurrent asyncio task using raw mode
- After agent execution: stop key listener, return to normal prompt mode
- Print one-shot shortcuts line before agent starts (static, showing default state actions)

### Terminal layout during execution

```
Step 3/25: Searching for 'USB-C hub' (1.2s)
  [B] Show browser  [V] More detail  [I] Instruct  [P] Pause  [Q] Quit
Step 4/25: Loading results (2.1s)
  [B] Show browser  [V] More detail  [I] Instruct  [P] Pause  [Q] Quit
```

Labels are action-based - they show what pressing the key **will do**, not the current state. For example, when the browser is visible, `[B]` shows "Minimise browser"; when hidden, it shows "Show browser".

## Regression testing notes

The following behaviours should be verified to prevent regression:

### Browser visibility
- **Browser starts minimised**: After `agent.browser_session.start()` completes, the browser window should be minimised via CDP before any agent steps run. The browser should NOT flash visibly on screen.
- **CDP minimize/restore works**: `_minimize_browser()` and `_restore_browser()` should successfully change `windowState` via `Browser.setWindowBounds`. Verify the window ID is cached after first lookup.
- **[B] key toggles visibility**: Pressing `b` should toggle `state.browser_visible`, and the next step callback should call the appropriate CDP method.
- **Auth/CAPTCHA auto-shows browser**: When `InterventionType.AUTH` or `InterventionType.CAPTCHA` fires, `state.browser_visible` is set to `True` and the browser is restored.
- **window_position=None**: The `BrowserProfile` must use `window_position=None` to prevent the default `--window-position=0,0` arg. Without this, the browser appears at (0,0) before minimize.

### Shortcuts display
- **Shortcuts line after each step**: The step callback prints a cyan shortcuts line after each step status line.
- **Action-based labels**: Labels show the action that will happen, not the current state (e.g. "Show browser" not "Browser: hidden").
- **Three locations consistent**: `runner.py` step callback, `cli.py` one-shot line, and `keyboard.py` `build_toolbar` all use the same action-based convention.

### Key handling
- **Raw mode during execution**: Key listener runs in prompt_toolkit raw mode during agent execution, not `prompt_async`.
- **[I] key exits raw mode**: Pressing `i` breaks out of raw mode to show the instruction prompt, then re-enters raw mode.
- **[Q] key raises interrupt**: Setting `quit_requested=True` causes the step callback to raise `KeyboardInterrupt`.

## File changes

**New dependency:**
- `prompt-toolkit>=3.0.50` in `pyproject.toml`

**Create:**
- `browser_agent/keyboard.py` - AgentState, KeyHandler, build_toolbar()

**Modify:**
- `browser_agent/cli.py` - prompt_toolkit PromptSession, patch_stdout, key listener task
- `browser_agent/runner.py` - AgentState flag checks in step callback, CDP minimize/restore methods, pre-start browser session
- `browser_agent/intervention.py` - Auto-show browser on auth/CAPTCHA, set state.browser_visible
- `browser_agent/display.py` - Respect dynamic verbose from AgentState
- `README.md` - Document keyboard shortcuts section
- `docs/interaction-spec.md` - Add keyboard shortcut section with key reference table

## Implementation updates (2026-02-16)

### Immediate key response
- `KeyHandler` now accepts `immediate_actions` dict mapping keys to async callbacks
- Callbacks are scheduled via `asyncio.create_task()` on keypress, bypassing the step-callback delay
- B (browser toggle) and Q (quit) fire within 1-2s instead of waiting for the next LLM call

### Persistent footer
- `FooterManager` class uses ANSI escape sequences to pin the shortcut bar to the terminal bottom row
- Sets a scroll region excluding the last row, so agent output scrolls above the fixed footer
- Refreshes automatically on keypress and after each agent step

### macOS browser control
- osascript `System Events` hides the browser instantly (like Cmd+H) - no Dock animation
- osascript `activate` reliably restores minimised/hidden windows on macOS
- CDP `setWindowBounds` kept as fallback for Linux/Windows
- Platform guard: `platform.system() == "Darwin"` protects all osascript code paths

### Auto-save session logs
- Session logs are saved to `logs/` automatically after each task completes
- Log path displayed in dim text after results
- "Export session summary" renamed to "View session log" in completion menu

### Terminal clear on agent start
- `FooterManager.start()` clears the terminal (`\033[2J\033[H`) before setting the scroll region
- Prevents fragments from the verbose prompt or greeting lingering on screen

### Intervention prompt handling
- Added `intervention_active` flag to `AgentState`
- Key listener exits raw mode when an intervention is active, so `Prompt.ask()` can read stdin normally
- `_run_intervention()` helper in runner suspends the footer and sets the flag before calling the handler, restores both in a `finally` block

### Log noise suppression
- `bubus` logger set to `CRITICAL` in `browse.py` to silence event bus timeout tracebacks
- `BrowserSession` and `watchdog_base` loggers set to `WARNING`
- Screenshot timeouts on heavy pages are recoverable and no longer clutter the output
