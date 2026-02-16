"""Tests for Azure OpenAI configuration loading and error formatting."""

import io
from unittest.mock import patch

import pytest
from rich.console import Console

from browser_agent.intervention import InterventionHandler
from browser_agent.keyboard import AgentState
from browser_agent.runner import AgentRunner


def _make_runner() -> AgentRunner:
    """Create a runner with captured console."""
    console = Console(file=io.StringIO(), force_terminal=True)
    state = AgentState()
    handler = InterventionHandler(console, state=state)
    return AgentRunner(console, handler, state=state)


def test_load_config_missing_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing AZURE_OPENAI_ENDPOINT raises ValueError."""
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    runner = _make_runner()
    with patch("browser_agent.runner.load_dotenv"), pytest.raises(ValueError, match="AZURE_OPENAI_ENDPOINT"):
        runner._load_config()


def test_load_config_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing AZURE_OPENAI_API_KEY raises ValueError."""
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com/")
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    runner = _make_runner()
    with patch("browser_agent.runner.load_dotenv"), pytest.raises(ValueError, match="AZURE_OPENAI_API_KEY"):
        runner._load_config()


def test_load_config_optional_api_version(monkeypatch: pytest.MonkeyPatch) -> None:
    """No crash when AZURE_OPENAI_API_VERSION is unset."""
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("AZURE_OPENAI_API_VERSION", raising=False)
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-41-mini")

    runner = _make_runner()
    with (
        patch("browser_agent.runner.load_dotenv"),
        patch("browser_agent.runner.ChatAzureOpenAI") as mock_chat,
    ):
        mock_chat.return_value = "mock-llm"
        result = runner._load_config()
    assert result == "mock-llm"
    # Verify api_version was NOT passed in kwargs
    call_kwargs = mock_chat.call_args[1]
    assert "api_version" not in call_kwargs


def test_load_config_returns_chat_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """_load_config returns a ChatAzureOpenAI instance when all vars are set."""
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-41-mini")

    runner = _make_runner()
    with (
        patch("browser_agent.runner.load_dotenv"),
        patch("browser_agent.runner.ChatAzureOpenAI") as mock_chat,
    ):
        mock_chat.return_value = "mock-llm"
        result = runner._load_config()
    assert result == "mock-llm"
    call_kwargs = mock_chat.call_args[1]
    assert call_kwargs["model"] == "gpt-41-mini"
    assert call_kwargs["api_version"] == "2024-12-01-preview"


def test_format_error_rate_limit() -> None:
    """'429' in error message produces rate limit guidance."""
    runner = _make_runner()
    error = Exception("Error 429: rate limit exceeded")
    msg = runner._format_error(error)
    assert "rate limit" in msg.lower()
    assert "429" not in msg  # Should be translated to friendly message
