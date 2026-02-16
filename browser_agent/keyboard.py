"""Keyboard shortcuts and agent state for interactive browser automation."""

import asyncio
import shutil
import sys
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from prompt_toolkit.formatted_text import HTML
from rich.console import Console


@dataclass
class AgentState:
    """Shared mutable state for keyboard-driven control during agent execution."""

    browser_visible: bool = False
    verbose: bool = False
    paused: bool = False
    pending_instruction: str | None = None
    quit_requested: bool = False
    running: bool = False


class KeyHandler:
    """Dispatches single keypresses to toggle agent state."""

    def __init__(
        self,
        state: AgentState,
        console: Console,
        immediate_actions: dict[str, Callable[[], Coroutine[Any, Any, None]]] | None = None,
    ) -> None:
        """Initialise the key handler.

        Args:
            state: Shared agent state
            console: Rich console for status output
            immediate_actions: Async callbacks fired immediately on keypress
        """
        self.state = state
        self.console = console
        self.immediate_actions = immediate_actions or {}
        self._background_tasks: set[asyncio.Task[None]] = set()

    def handle_key(self, key: str) -> None:
        """Dispatch a single keypress to the appropriate state toggle.

        Fires any registered immediate-action callback for the key via
        asyncio.create_task() so it runs without waiting for the next
        agent step.

        Args:
            key: The key that was pressed
        """
        if key == "b":
            self.state.browser_visible = not self.state.browser_visible
            status = "visible" if self.state.browser_visible else "hidden"
            self.console.print(f"[dim]Browser: {status}[/dim]")
        elif key == "v":
            self.state.verbose = not self.state.verbose
            status = "on" if self.state.verbose else "off"
            self.console.print(f"[dim]Verbose: {status}[/dim]")
        elif key == "i":
            self.state.paused = True
        elif key == "p":
            self.state.paused = not self.state.paused
            status = "paused" if self.state.paused else "resumed"
            self.console.print(f"[dim]Agent {status}[/dim]")
        elif key == "q":
            self.state.quit_requested = True

        # Schedule immediate async callback if registered for this key
        if key in self.immediate_actions:
            try:
                loop = asyncio.get_running_loop()
                task = loop.create_task(self.immediate_actions[key]())
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)
            except RuntimeError:
                pass  # No running event loop - skip async callback


def build_toolbar(state: AgentState) -> HTML:
    """Build the prompt_toolkit bottom toolbar showing current state and shortcuts.

    Args:
        state: Current agent state

    Returns:
        Formatted HTML for the toolbar
    """
    if not state.running:
        return HTML("")

    parts = [
        f"<b>[B]</b> {'Minimise' if state.browser_visible else 'Show'} browser",
        f"<b>[V]</b> {'Less detail' if state.verbose else 'More detail'}",
        "<b>[I]</b> Instruct",
    ]

    if state.paused:
        parts.append("<b>[P]</b> Resume")
    else:
        parts.append("<b>[P]</b> Pause")

    parts.append("<b>[Q]</b> Quit")

    return HTML("  ".join(parts))


class FooterManager:
    """Pins a shortcut bar to the bottom terminal row using ANSI escape sequences.

    Uses a scroll region that excludes the last row, then writes the
    shortcut bar there with save/restore cursor so normal output scrolls
    above the fixed footer.
    """

    def __init__(self, state: AgentState) -> None:
        self.state = state
        self._active = False

    def _term_height(self) -> int:
        return shutil.get_terminal_size((80, 24)).lines

    def _term_width(self) -> int:
        return shutil.get_terminal_size((80, 24)).columns

    def _write(self, data: str) -> None:
        sys.stdout.write(data)
        sys.stdout.flush()

    def start(self) -> None:
        """Set the scroll region and draw the initial footer."""
        h = self._term_height()
        # Set scroll region to rows 1..(h-1), leaving the last row free
        self._write(f"\033[1;{h - 1}r")
        self._active = True
        self.refresh()

    def stop(self) -> None:
        """Reset the scroll region and clear the footer row."""
        if not self._active:
            return
        h = self._term_height()
        # Reset scroll region to full terminal
        self._write(f"\033[1;{h}r")
        # Move to last row and clear it
        self._write(f"\033[{h};1H\033[2K")
        self._active = False

    def refresh(self) -> None:
        """Redraw the footer with current shortcut labels."""
        if not self._active:
            return

        h = self._term_height()
        w = self._term_width()

        browser_action = "Minimise" if self.state.browser_visible else "Show"
        verbose_action = "Less detail" if self.state.verbose else "More detail"
        pause_action = "Resume" if self.state.paused else "Pause"

        text = f" [B] {browser_action} browser  [V] {verbose_action}  [I] Instruct  [P] {pause_action}  [Q] Quit"

        # Pad/truncate to terminal width
        text = text[:w].ljust(w)

        # Save cursor, move to last row, write in reverse video, restore cursor
        self._write(f"\0337\033[{h};1H\033[7m{text}\033[0m\0338")
