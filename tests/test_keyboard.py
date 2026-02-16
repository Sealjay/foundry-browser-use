"""Tests for keyboard shortcuts, agent state, and toolbar/footer."""

import io

from rich.console import Console

from browser_agent.keyboard import AgentState, FooterManager, KeyHandler, build_toolbar


def test_key_b_toggles_browser_visible(agent_state: AgentState, console: Console) -> None:
    """Pressing 'b' flips browser_visible."""
    handler = KeyHandler(agent_state, console)
    assert agent_state.browser_visible is False
    handler.handle_key("b")
    assert agent_state.browser_visible is True
    handler.handle_key("b")
    assert agent_state.browser_visible is False


def test_key_v_toggles_verbose(agent_state: AgentState, console: Console) -> None:
    """Pressing 'v' flips verbose."""
    handler = KeyHandler(agent_state, console)
    assert agent_state.verbose is False
    handler.handle_key("v")
    assert agent_state.verbose is True


def test_key_i_sets_paused(agent_state: AgentState, console: Console) -> None:
    """Pressing 'i' sets paused to True (to prompt for instruction)."""
    handler = KeyHandler(agent_state, console)
    handler.handle_key("i")
    assert agent_state.paused is True


def test_key_p_toggles_paused(agent_state: AgentState, console: Console) -> None:
    """Pressing 'p' twice toggles paused."""
    handler = KeyHandler(agent_state, console)
    handler.handle_key("p")
    assert agent_state.paused is True
    handler.handle_key("p")
    assert agent_state.paused is False


def test_key_q_sets_quit(agent_state: AgentState, console: Console) -> None:
    """Pressing 'q' sets quit_requested."""
    handler = KeyHandler(agent_state, console)
    handler.handle_key("q")
    assert agent_state.quit_requested is True


def test_key_f_toggles_vision(agent_state: AgentState, console: Console) -> None:
    """Pressing 'f' flips vision_enabled."""
    handler = KeyHandler(agent_state, console)
    assert agent_state.vision_enabled is False
    handler.handle_key("f")
    assert agent_state.vision_enabled is True
    handler.handle_key("f")
    assert agent_state.vision_enabled is False


def test_build_toolbar_shows_actions(agent_state: AgentState) -> None:
    """Toolbar shows contextual labels based on state."""
    agent_state.running = True
    result = build_toolbar(agent_state)
    # When browser is hidden, should say "Show"
    assert "Show" in result.value
    assert "browser" in result.value.lower()

    agent_state.browser_visible = True
    result = build_toolbar(agent_state)
    assert "Minimise" in result.value


def test_build_toolbar_empty_when_not_running(agent_state: AgentState) -> None:
    """Toolbar returns empty HTML when agent is not running."""
    agent_state.running = False
    result = build_toolbar(agent_state)
    assert result.value == ""


def test_build_toolbar_shows_vision_status(agent_state: AgentState) -> None:
    """Toolbar shows 'Enable vision' when off, 'Disable vision' when on."""
    agent_state.running = True
    result = build_toolbar(agent_state)
    assert "Enable" in result.value
    assert "vision" in result.value.lower()

    agent_state.vision_enabled = True
    result = build_toolbar(agent_state)
    assert "Disable" in result.value


def test_footer_manager_refresh_content(agent_state: AgentState) -> None:
    """FooterManager.refresh writes footer text containing shortcut labels."""
    buf = io.StringIO()
    agent_state.running = True

    footer = FooterManager(agent_state)
    # Override _write to capture output and ensure wide terminal
    footer._write = buf.write  # type: ignore[assignment]
    footer._term_width = lambda: 200  # type: ignore[assignment]
    footer._active = True
    footer.refresh()

    output = buf.getvalue()
    assert "[B]" in output
    assert "[V]" in output
    assert "[F]" in output
    assert "[Q]" in output
