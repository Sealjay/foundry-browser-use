"""Tests for browser visibility toggling and BrowserProfile construction."""

import io
from unittest.mock import AsyncMock, MagicMock, patch

from rich.console import Console

from browser_agent.intervention import InterventionHandler
from browser_agent.keyboard import AgentState
from browser_agent.runner import AgentRunner


def _make_runner(state: AgentState | None = None) -> AgentRunner:
    """Create a runner with captured console and optional state."""
    console = Console(file=io.StringIO(), force_terminal=True)
    st = state or AgentState()
    handler = InterventionHandler(console, state=st)
    return AgentRunner(console, handler, state=st)


def test_browser_profile_no_window_position() -> None:
    """BrowserProfile with window_position=None omits --window-position arg."""
    from browser_use.browser.profile import BrowserProfile

    profile = BrowserProfile(window_position=None)
    # window_position should be None - not setting a default position
    assert profile.window_position is None


def test_browser_profile_window_size() -> None:
    """BrowserProfile accepts a dict for window_size."""
    from browser_use.browser.profile import BrowserProfile

    profile = BrowserProfile(
        window_size={"width": 1280, "height": 900},  # type: ignore[arg-type]
    )
    # Should have been accepted (pydantic coercion or plain dict)
    assert profile.window_size is not None


def test_toggle_browser_visible_calls_restore() -> None:
    """When browser_visible is True, toggle_browser_immediate calls _restore_browser."""
    state = AgentState(browser_visible=True)
    runner = _make_runner(state)
    runner._agent = MagicMock()
    runner._restore_browser = AsyncMock()  # type: ignore[assignment]
    runner._minimize_browser = AsyncMock()  # type: ignore[assignment]

    import asyncio

    asyncio.get_event_loop().run_until_complete(runner.toggle_browser_immediate())
    runner._restore_browser.assert_called_once()
    runner._minimize_browser.assert_not_called()


def test_toggle_browser_visible_calls_minimize() -> None:
    """When browser_visible is False, toggle_browser_immediate calls _minimize_browser."""
    state = AgentState(browser_visible=False)
    runner = _make_runner(state)
    runner._agent = MagicMock()
    runner._restore_browser = AsyncMock()  # type: ignore[assignment]
    runner._minimize_browser = AsyncMock()  # type: ignore[assignment]

    import asyncio

    asyncio.get_event_loop().run_until_complete(runner.toggle_browser_immediate())
    runner._minimize_browser.assert_called_once()
    runner._restore_browser.assert_not_called()


def test_auth_intervention_auto_shows(agent_state: AgentState, console: Console) -> None:
    """Auth handler sets browser_visible = True."""
    handler = InterventionHandler(console, state=agent_state)
    from browser_agent.intervention import InterventionContext, InterventionType

    context = InterventionContext(intervention_type=InterventionType.AUTH, step_number=1, max_steps=25)
    with patch("rich.prompt.Prompt.ask", return_value=""):
        handler.handle_auth(context)
    assert agent_state.browser_visible is True
