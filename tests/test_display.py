"""Tests for result formatting and display output."""

import io
import json
import re

from rich.console import Console

from browser_agent.display import ResultFormatter


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def test_format_time_seconds() -> None:
    """Times under 60s format as seconds."""
    console = Console(file=io.StringIO())
    formatter = ResultFormatter(console)
    assert formatter.format_time(45.2) == "45.2s"


def test_format_time_minutes() -> None:
    """Times over 60s format as minutes and seconds."""
    console = Console(file=io.StringIO())
    formatter = ResultFormatter(console)
    assert formatter.format_time(125) == "2m 5s"


def test_show_success_output() -> None:
    """show_success writes a checkmark, step count, and time."""
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True)
    formatter = ResultFormatter(console)
    formatter.show_success(5, 12.3, {"Summary": "Found 3 items"})
    output = _strip_ansi(buf.getvalue())
    assert "5" in output
    assert "steps" in output
    assert "12.3s" in output


def test_show_json_result(capsys) -> None:
    """show_json_result outputs valid JSON with expected keys."""
    console = Console(file=io.StringIO())
    formatter = ResultFormatter(console)
    formatter.show_json_result(
        summary="Task done",
        structured_data={"url": "https://example.com"},
        steps=3,
        elapsed=5.0,
        success=True,
    )
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["summary"] == "Task done"
    assert data["success"] is True
    assert data["steps"] == 3
    assert "url" in data["data"]
