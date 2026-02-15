# Multi-turn sessions design

**Date:** 2026-02-15
**Status:** Approved

## Problem

The CLI currently treats each task as independent. Users cannot say "now compare those 3 options" because the agent has no memory of what happened before. Task results are shown as plain text with no structured export, making it hard to continue work in Claude Code or other tools.

## Goals

1. Tasks within a session share context - follow-up tasks understand prior results
2. Task summarisation with three output modes (default, verbose, structured JSON)
3. Smarter interventions - checkpoints, confidence-based step-in, batched upfront questions
4. Terminal bell when the agent needs attention
5. Summary export as portable prompt for Claude Code or disk
6. README and interaction spec updates

## Approach: Session log with LLM-generated summaries

After each task completes, the LLM generates a concise summary. That summary - not raw history - is injected into the next task's prompt as context. Full actions are always logged internally for export.

## Architecture

### New module: `browser_agent/session.py`

**`TaskRecord`** dataclass:
- `task: str` - original user prompt
- `summary: str` - LLM-generated concise summary (populated after completion)
- `structured_data: dict[str, str]` - key-value findings (URLs, prices, names)
- `steps_taken: int`, `elapsed: float` - metrics
- `success: bool`
- `actions_log: list[str]` - every step description, always recorded

**`Session`** class:
- `records: list[TaskRecord]` - all tasks in this session
- `verbose: bool` - whether to show actions in output
- `build_context_prompt() -> str` - generates context from prior summaries for the next task. Last 5 summaries in full, earlier ones condensed to one line. Returns empty string if no prior tasks.
- `export_summary() -> str` - returns self-contained markdown with all tasks, summaries, structured data, and a suggested follow-up prompt
- `save_to_disk(path: str) -> None` - writes export to file
- `add_record(record: TaskRecord) -> None` - appends a completed task

### Multi-turn context flow

1. User enters task
2. `Session.build_context_prompt()` generates context from prior `TaskRecord.summary` values
3. Agent prompt becomes: `"{context}\n\nNew task: {user_task}"`
4. Agent runs with awareness of prior tasks
5. On completion, LLM generates summary via a second call
6. `TaskRecord` appended to session

Context cap: if 10+ tasks, only last 5 summaries in full; earlier ones as one-liners.

### Summary generation

In `runner.py`'s `_done_callback`, make one additional LLM call with the agent's result + actions log. Prompt asks for:
1. A 1-3 sentence findings summary
2. Structured key-value data (if any)

Response is parsed and stored in the `TaskRecord`.

### Output modes

**Default (interactive):** Findings-only in chat. `ResultFormatter` displays summary + structured data.

**Verbose (`--verbose` flag or opt-in at session start):** Actions + findings. Each step shown during execution (already works), plus full actions log in completion summary.

**Structured (`--json` flag, non-interactive):** For `run_task.py`. Outputs JSON with `summary`, `structured_data`, `steps`, `elapsed`, `success`. For piping to other tools.

### Export

New completion menu option: "Export session summary". Writes markdown to `./browse-session-YYYYMMDD-HHMMSS.md`. Contains all task summaries, structured data, and a suggested follow-up prompt formatted for Claude Code.

### Intervention enhancements

**Terminal bell:** Print `\a` before every intervention prompt. Works with iTerm2 and most terminals.

**Batched upfront questions:** Before agent starts, one LLM call analyses the task for likely ambiguities. Generates 0-3 clarifying questions. If none, agent starts immediately. Questions shown in a numbered list; user answers all at once.

**New intervention types** added to `InterventionType` enum:

- `CHECKPOINT` - triggered on phase transitions detected in `next_goal` (searching to comparing, reading to submitting). Shows brief progress summary, asks "Continue or adjust?"
- `CONFIDENCE` - triggered when LLM evaluation contains hedging language ("unsure", "might", "could be"). Shows uncertainty, asks user to decide.
- `SUB_GOAL_COMPLETE` - triggered when LLM evaluation indicates a sub-goal is done. Shows mini-summary, asks "What next?"

### File changes

**Create:**
- `browser_agent/session.py` - Session, TaskRecord

**Modify:**
- `browser_agent/runner.py` - summary generation, context injection, checkpoint/confidence detection
- `browser_agent/intervention.py` - new types + handlers, terminal bell
- `browser_agent/display.py` - verbose display, export formatting, JSON output
- `browser_agent/cli.py` - flags, Session integration, export option, upfront questions
- `run_task.py` - `--json` flag
- `browse.py` - CLI args passthrough
- `README.md` - document multi-turn, modes, interventions
- `docs/interaction-spec.md` - new intervention types, session flow
