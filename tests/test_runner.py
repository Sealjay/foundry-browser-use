"""Tests for agent runner logic: phase classification, detection, formatting."""

import io
from unittest.mock import MagicMock

from rich.console import Console

from browser_agent.intervention import InterventionHandler
from browser_agent.keyboard import AgentState
from browser_agent.runner import AgentRunner


def _make_runner() -> AgentRunner:
    """Create a runner with captured console and mock handler."""
    console = Console(file=io.StringIO(), force_terminal=True)
    state = AgentState()
    handler = InterventionHandler(console, state=state)
    return AgentRunner(console, handler, state=state)


# --- Phase classification ---


def test_classify_phase_searching() -> None:
    """'search for USB hubs' classifies as 'searching'."""
    runner = _make_runner()
    assert runner._classify_phase("search for USB hubs") == "searching"


def test_classify_phase_comparing() -> None:
    """'compare prices' classifies as 'comparing'."""
    runner = _make_runner()
    assert runner._classify_phase("compare prices of laptops") == "comparing"


def test_classify_phase_unknown() -> None:
    """'processing data' does not match any phase."""
    runner = _make_runner()
    assert runner._classify_phase("processing data") == ""


# --- Hedging detection ---


def test_detect_hedging_true() -> None:
    """Hedging language is detected in evaluation text."""
    runner = _make_runner()
    assert runner._detect_hedging("unsure about this result") is True


def test_detect_hedging_false() -> None:
    """Non-hedging language is not flagged."""
    runner = _make_runner()
    assert runner._detect_hedging("found the answer successfully") is False


# --- Completion detection ---


def test_detect_completion_true() -> None:
    """Completion language is detected."""
    runner = _make_runner()
    assert runner._detect_completion("successfully found 3 items") is True


def test_detect_completion_false() -> None:
    """Non-completion language is not flagged."""
    runner = _make_runner()
    assert runner._detect_completion("still working on it") is False


# --- Failure detection ---


def test_check_for_failure() -> None:
    """Agent output with 'failure' in evaluation is detected."""
    runner = _make_runner()
    mock_output = MagicMock()
    mock_output.evaluation_previous_goal = "failure: could not click button"
    assert runner._check_for_failure(mock_output) is True


def test_check_for_failure_no_failure() -> None:
    """Agent output without failure language is not flagged."""
    runner = _make_runner()
    mock_output = MagicMock()
    mock_output.evaluation_previous_goal = "success: page loaded"
    assert runner._check_for_failure(mock_output) is False


# --- Word similarity ---


def test_word_similarity_identical() -> None:
    """Identical strings have similarity 1.0."""
    runner = _make_runner()
    assert runner._word_similarity("hello world", "hello world") == 1.0


def test_word_similarity_disjoint() -> None:
    """Strings with no shared words have similarity 0.0."""
    runner = _make_runner()
    assert runner._word_similarity("hello world", "foo bar") == 0.0


def test_word_similarity_partial() -> None:
    """Partially overlapping strings have intermediate similarity."""
    runner = _make_runner()
    sim = runner._word_similarity("hello world foo", "hello bar foo")
    assert 0.0 < sim < 1.0


# --- Repetition detection ---


def test_detect_repetition_within_window() -> None:
    """Three similar actions in a window are detected as repetitive."""
    runner = _make_runner()
    runner.actions_log = [
        "clicking the search button on the page",
        "clicking the search button on page",
        "clicking search button on the page",
    ]
    assert runner._detect_repetition(window=3, threshold=0.7) is True


def test_detect_repetition_insufficient_actions() -> None:
    """Fewer actions than window size returns False."""
    runner = _make_runner()
    runner.actions_log = ["action one"]
    assert runner._detect_repetition(window=3) is False


# --- Step status formatting ---


def test_format_step_status() -> None:
    """Step status includes step number and description."""
    runner = _make_runner()
    runner.max_steps = 25
    status = runner._format_step_status(3, "Navigating to page", 2.5)
    assert "Step 3/25" in status
    assert "Navigating to page" in status
    assert "2.5s" in status


def test_format_step_status_no_elapsed() -> None:
    """Step status without elapsed time omits the timing."""
    runner = _make_runner()
    runner.max_steps = 25
    status = runner._format_step_status(1, "Starting", elapsed=0.5)
    assert "0.5s" not in status  # Below 1.0s threshold
