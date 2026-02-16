"""Shared fixtures for browser agent tests."""

import io
from unittest.mock import MagicMock

import pytest
from rich.console import Console

from browser_agent.intervention import InterventionHandler
from browser_agent.keyboard import AgentState
from browser_agent.session import Session, TaskRecord


@pytest.fixture
def agent_state() -> AgentState:
    """Fresh AgentState instance."""
    return AgentState()


@pytest.fixture
def console() -> Console:
    """Console that captures output to a StringIO buffer."""
    return Console(file=io.StringIO(), force_terminal=True)


@pytest.fixture
def mock_llm() -> MagicMock:
    """Mock ChatAzureOpenAI that returns canned responses."""
    llm = MagicMock()
    llm.ainvoke = MagicMock()
    return llm


@pytest.fixture
def intervention_handler(console: Console, agent_state: AgentState) -> InterventionHandler:
    """InterventionHandler wired to captured console and state."""
    return InterventionHandler(console, state=agent_state)


@pytest.fixture
def session() -> Session:
    """Fresh Session instance."""
    return Session()


@pytest.fixture
def sample_task_record() -> TaskRecord:
    """Pre-populated TaskRecord for testing."""
    return TaskRecord(
        task="Find the top 3 wireless keyboards under £50",
        summary="Found 3 keyboards: Logitech K380 £29.99, Anker A7726 £25.99, iClever BK10 £33.99",
        structured_data={"keyboard_1": "Logitech K380 £29.99", "keyboard_2": "Anker A7726 £25.99"},
        steps_taken=9,
        elapsed=16.3,
        success=True,
        actions_log=["Opening Amazon UK", "Searching for wireless keyboards", "Extracting results"],
    )
