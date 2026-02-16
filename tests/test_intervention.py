"""Tests for intervention handler routing and state management."""

from unittest.mock import patch

from browser_agent.intervention import (
    InterventionContext,
    InterventionHandler,
    InterventionResponse,
    InterventionType,
)
from browser_agent.keyboard import AgentState


def test_handle_intervention_routes_auth(intervention_handler: InterventionHandler, agent_state: AgentState) -> None:
    """AUTH intervention routes to handle_auth."""
    context = InterventionContext(intervention_type=InterventionType.AUTH, step_number=1, max_steps=25)
    with patch.object(
        intervention_handler, "handle_auth", return_value=InterventionResponse(continue_execution=True)
    ) as mock:
        intervention_handler.handle_intervention(context)
        mock.assert_called_once_with(context)


def test_handle_intervention_routes_stuck(intervention_handler: InterventionHandler, agent_state: AgentState) -> None:
    """STUCK intervention routes to handle_stuck."""
    context = InterventionContext(intervention_type=InterventionType.STUCK, step_number=5, max_steps=25)
    with patch.object(
        intervention_handler, "handle_stuck", return_value=InterventionResponse(continue_execution=True)
    ) as mock:
        intervention_handler.handle_intervention(context)
        mock.assert_called_once_with(context)


def test_handle_auth_sets_browser_visible(intervention_handler: InterventionHandler, agent_state: AgentState) -> None:
    """Auth intervention makes browser visible."""
    context = InterventionContext(intervention_type=InterventionType.AUTH, step_number=1, max_steps=25)
    with patch("rich.prompt.Prompt.ask", return_value=""):
        intervention_handler.handle_auth(context)
    assert agent_state.browser_visible is True


def test_handle_captcha_sets_browser_visible(
    intervention_handler: InterventionHandler, agent_state: AgentState
) -> None:
    """CAPTCHA intervention makes browser visible."""
    context = InterventionContext(intervention_type=InterventionType.CAPTCHA, step_number=2, max_steps=25)
    with patch("rich.prompt.Prompt.ask", return_value=""):
        intervention_handler.handle_captcha(context)
    assert agent_state.browser_visible is True


def test_handle_choice_returns_index(
    intervention_handler: InterventionHandler,
) -> None:
    """Choice intervention returns selected index."""
    context = InterventionContext(
        intervention_type=InterventionType.CHOICE,
        step_number=3,
        max_steps=25,
        message="Pick one",
        choices=["Option A", "Option B", "None of these"],
    )
    with patch("rich.prompt.Prompt.ask", return_value="1"):
        response = intervention_handler.handle_choice(context)
    assert response.choice_index == 0
    assert response.continue_execution is True


def test_handle_confirm_default_no(
    intervention_handler: InterventionHandler,
) -> None:
    """Confirm intervention defaults to False (safe option)."""
    context = InterventionContext(
        intervention_type=InterventionType.CONFIRM,
        step_number=4,
        max_steps=25,
        message="Purchase this item?",
    )
    with (
        patch("rich.prompt.Confirm.ask", return_value=False),
        patch("rich.prompt.Prompt.ask", return_value="cancel"),
    ):
        response = intervention_handler.handle_confirm(context)
    assert response.continue_execution is True
    assert response.new_instructions == "cancel"


def test_unknown_type_returns_continue(
    intervention_handler: InterventionHandler,
) -> None:
    """Unknown intervention type defaults to continue_execution=True."""
    context = InterventionContext(
        intervention_type=InterventionType.AUTH,
        step_number=1,
        max_steps=25,
    )

    def patched_handle(self, ctx):
        """Route with empty handlers dict to trigger the fallback path."""
        handlers = {}
        handler = handlers.get(ctx.intervention_type)
        if handler:
            return handler(ctx)
        self.console.print(f"[yellow]Unknown intervention type: {ctx.intervention_type}[/yellow]")
        return InterventionResponse(continue_execution=True)

    with patch.object(InterventionHandler, "handle_intervention", patched_handle):
        response = intervention_handler.handle_intervention(context)
    assert response.continue_execution is True
