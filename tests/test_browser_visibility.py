"""Tests for browser visibility toggling and BrowserProfile construction."""

import io
import platform
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
    """BrowserProfile accepts a dict for window_size and preserves it in headful mode.

    BrowserProfile.detect_display_configuration() auto-detects headless=True
    when no display is available (e.g. CI runners with no X server) and
    clears window_size in that mode, since headless Chromium has no OS
    window to size. The app always runs headful (browser_agent/runner.py
    starts the browser headed, then minimises it via CDP), so pin
    headless=False here to exercise that same path deterministically
    instead of depending on whatever display the test happens to run on.
    """
    from browser_use.browser.profile import BrowserProfile

    profile = BrowserProfile(
        headless=False,
        window_size={"width": 1280, "height": 900},  # type: ignore[arg-type]
    )
    # Accepted and coerced (pydantic ViewportSize), values preserved.
    assert profile.window_size is not None
    assert profile.window_size["width"] == 1280
    assert profile.window_size["height"] == 900


def test_get_browser_app_name_reads_watchdog_subprocess() -> None:
    """_get_browser_app_name resolves the .app bundle via the local browser
    watchdog's psutil.Process, not browser_session.browser (removed in
    browser-use 0.13: BrowserSession launches the browser as a raw CDP
    subprocess now, there's no Playwright Browser wrapper to reach into
    any more -- see runner.py:_get_browser_app_name).
    """
    runner = _make_runner()
    runner._agent = MagicMock()
    runner._agent.browser_session._local_browser_watchdog._subprocess.exe.return_value = (
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    )

    name = runner._get_browser_app_name()

    if platform.system() == "Darwin":
        assert name == "Google Chrome"
    else:
        assert name is None


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
