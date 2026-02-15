"""Keyboard shortcuts and agent state for interactive browser automation."""

import contextlib
from dataclasses import dataclass

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

    def __init__(self, state: AgentState, console: Console) -> None:
        """Initialise the key handler.

        Args:
            state: Shared agent state
            console: Rich console for status output
        """
        self.state = state
        self.console = console

    def handle_key(self, key: str) -> None:
        """Dispatch a single keypress to the appropriate state toggle.

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

    async def show_browser(self, cdp_client, window_id: int) -> None:
        """Restore the browser window from minimised state via CDP."""
        with contextlib.suppress(Exception):
            await cdp_client.send.Browser.setWindowBounds({"windowId": window_id, "bounds": {"windowState": "normal"}})

    async def hide_browser(self, cdp_client, window_id: int) -> None:
        """Minimise the browser window via CDP."""
        with contextlib.suppress(Exception):
            await cdp_client.send.Browser.setWindowBounds(
                {"windowId": window_id, "bounds": {"windowState": "minimized"}}
            )


def build_toolbar(state: AgentState) -> HTML:
    """Build the prompt_toolkit bottom toolbar showing current state and shortcuts.

    Args:
        state: Current agent state

    Returns:
        Formatted HTML for the toolbar
    """
    if not state.running:
        return HTML("")

    browser_status = "visible" if state.browser_visible else "hidden"
    verbose_status = "on" if state.verbose else "off"

    parts = [
        f"<b>[B]</b> Browser: {browser_status}",
        f"<b>[V]</b> Verbose: {verbose_status}",
        "<b>[I]</b> Instruct",
    ]

    if state.paused:
        parts.append("<b>[P]</b> Paused")
    else:
        parts.append("<b>[P]</b> Pause")

    parts.append("<b>[Q]</b> Quit")

    return HTML("  ".join(parts))
