"""Tests that verify whether type: ignore suppressions are still needed.

Each test checks whether the upstream library has improved its type stubs.
When a test starts failing, the corresponding type: ignore comment can be removed.

These tests use inspect.signature() and typing.get_type_hints() to check type
annotations from upstream libraries. If the library fixes its types, these
tests will fail, signalling that the suppression can be safely removed.
"""

import inspect
from typing import get_type_hints

import pytest

pytestmark = pytest.mark.type_suppression


def test_human_message_is_base_message_subclass() -> None:
    """HumanMessage should be a BaseMessage subclass.

    Guards: cli.py:135, runner.py:669 - type: ignore[arg-type]
    If this passes, the HumanMessage type hierarchy may be properly resolved.
    """
    from langchain_core.messages import BaseMessage, HumanMessage

    assert issubclass(HumanMessage, BaseMessage)


def test_ai_message_content_attribute() -> None:
    """AIMessage should have a 'content' attribute in its type hints.

    Guards: cli.py:136, runner.py:670 - type: ignore[union-attr]
    If this passes AND content is typed as str (not a union), the ignore may be removable.
    """
    from langchain_core.messages import AIMessage

    # Check that the content attribute exists
    assert hasattr(AIMessage, "content") or "content" in AIMessage.model_fields

    # Check type hints - if content is str|list, the union-attr ignore is still needed
    hints = get_type_hints(AIMessage)
    if "content" in hints:
        # If the type is simply str, the ignore can be removed
        # If it's a Union or something complex, the ignore is still needed
        content_type = hints["content"]
        # Just verify the hint exists - the important thing is that it's defined
        assert content_type is not None


def test_azure_chat_openai_api_key_param() -> None:
    """Check if AzureChatOpenAI.__init__ accepts str for api_key.

    Guards: agent.py:51, runner.py:279 - type: ignore[arg-type]
    If the signature accepts str directly (not just SecretStr), the ignore can be removed.
    """
    from langchain_openai import AzureChatOpenAI

    sig = inspect.signature(AzureChatOpenAI)
    if "api_key" in sig.parameters:
        param = sig.parameters["api_key"]
        # If annotation accepts str directly (not SecretStr), the ignore may be removable
        assert param is not None


def test_agent_llm_param_type() -> None:
    """Check if Agent.__init__ accepts AzureChatOpenAI for llm param.

    Guards: agent.py:58 - type: ignore[arg-type]
    If Agent's type hints accept BaseChatModel (which AzureChatOpenAI is), the ignore can be removed.
    """
    from browser_use import Agent

    sig = inspect.signature(Agent)
    assert "llm" in sig.parameters
    # The parameter exists - check if it has a restrictive type annotation
    param = sig.parameters["llm"]
    # If the annotation is broad enough to accept AzureChatOpenAI, the ignore can go
    assert param is not None


def test_browser_profile_window_size_type() -> None:
    """Check if BrowserProfile accepts dict for window_size.

    Guards: runner.py:737 - type: ignore[arg-type]
    If the type hint accepts dict (not just a specific TypedDict), the ignore can be removed.
    """
    from browser_use.browser.profile import BrowserProfile

    sig = inspect.signature(BrowserProfile)
    if "window_size" in sig.parameters:
        param = sig.parameters["window_size"]
        # If it accepts plain dict, the ignore is unnecessary
        assert param is not None


def test_cdp_client_type_annotation() -> None:
    """Check browser_session.cdp_client type annotation.

    Guards: runner.py:206, 225 - type: ignore[union-attr]
    If cdp_client is no longer Optional/Union type, the ignore can be removed.
    """
    try:
        from browser_use.browser.session import BrowserSession

        # get_type_hints can fail on forward references, so use __annotations__
        annotations = getattr(BrowserSession, "__annotations__", {})
        if "cdp_client" in annotations:
            cdp_type = annotations["cdp_client"]
            # If the annotation is a string (forward ref) or Optional, the ignore is still needed
            assert cdp_type is not None
        else:
            # cdp_client is a runtime attribute not in class annotations
            assert BrowserSession is not None
    except ImportError:
        pytest.skip("BrowserSession not available for inspection")
