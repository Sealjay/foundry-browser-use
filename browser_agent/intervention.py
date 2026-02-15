"""Human intervention handlers for browser automation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from browser_agent.keyboard import AgentState

from rich.console import Console
from rich.prompt import Confirm, Prompt


class InterventionType(Enum):
    """Types of human intervention required during automation."""

    AUTH = "auth"
    CAPTCHA = "captcha"
    CHOICE = "choice"
    CONFIRM = "confirm"
    STUCK = "stuck"
    MAX_STEPS = "max_steps"
    CHECKPOINT = "checkpoint"
    CONFIDENCE = "confidence"
    SUB_GOAL_COMPLETE = "sub_goal_complete"


@dataclass
class InterventionContext:
    """Context data for an intervention request."""

    intervention_type: InterventionType
    step_number: int
    max_steps: int
    message: str | None = None
    choices: list[str] | None = None
    default_choice: int | None = None
    action_summary: dict[str, str] | None = None
    progress_summary: str | None = None
    confidence_detail: str | None = None


@dataclass
class InterventionResponse:
    """User's response to an intervention request."""

    continue_execution: bool
    choice_index: int | None = None
    new_instructions: str | None = None
    increase_steps: bool = False


class InterventionHandler:
    """Handles human intervention prompts during automation."""

    def __init__(self, console: Console, state: AgentState | None = None):
        """Initialise the intervention handler.

        Args:
            console: Rich console for output
            state: Optional agent state for browser visibility control
        """
        self.console = console
        self.state = state

    def _ring_bell(self) -> None:
        """Ring the terminal bell to alert the user."""
        print("\a", end="", flush=True)

    def handle_auth(self, context: InterventionContext) -> InterventionResponse:
        """Handle authentication required intervention.

        Args:
            context: Intervention context

        Returns:
            User's response
        """
        self._ring_bell()
        if self.state:
            self.state.browser_visible = True
            self.console.print("[dim]Browser window shown for authentication.[/dim]")
        self.console.print()
        self.console.print("The site requires authentication. Please log in manually in the browser window.")
        Prompt.ask("Press Enter when you've logged in to continue", default="")
        return InterventionResponse(continue_execution=True)

    def handle_captcha(self, context: InterventionContext) -> InterventionResponse:
        """Handle CAPTCHA/verification intervention.

        Args:
            context: Intervention context

        Returns:
            User's response
        """
        self._ring_bell()
        if self.state:
            self.state.browser_visible = True
            self.console.print("[dim]Browser window shown for verification.[/dim]")
        self.console.print()
        self.console.print("Please solve the CAPTCHA in the browser window.")
        Prompt.ask("Press Enter when you've completed it", default="")
        return InterventionResponse(continue_execution=True)

    def handle_choice(self, context: InterventionContext) -> InterventionResponse:
        """Handle ambiguous choice intervention.

        Args:
            context: Intervention context

        Returns:
            User's response
        """
        self._ring_bell()
        self.console.print()
        if context.message:
            self.console.print(context.message)
            self.console.print()

        if not context.choices:
            return InterventionResponse(continue_execution=False)

        # Display numbered choices
        for i, choice in enumerate(context.choices, 1):
            self.console.print(f"  {i}. {choice}")

        # Get user selection
        default_str = str(context.default_choice) if context.default_choice else str(1)
        choice_str = Prompt.ask("Which would you like?", default=default_str)

        try:
            choice_idx = int(choice_str) - 1

            # Check if "None of these" was selected (last option)
            if choice_idx == len(context.choices) - 1:
                new_instructions = Prompt.ask("How would you like to refine the search?")
                return InterventionResponse(continue_execution=True, new_instructions=new_instructions)

            return InterventionResponse(continue_execution=True, choice_index=choice_idx)
        except (ValueError, IndexError):
            self.console.print("[yellow]Invalid choice. Using default.[/yellow]")
            return InterventionResponse(continue_execution=True, choice_index=context.default_choice or 0)

    def handle_confirm(self, context: InterventionContext) -> InterventionResponse:
        """Handle confirmation before action intervention.

        Args:
            context: Intervention context

        Returns:
            User's response
        """
        self._ring_bell()
        self.console.print()
        if context.message:
            self.console.print(context.message)

        if context.action_summary:
            for key, value in context.action_summary.items():
                self.console.print(f"  {key}: {value}")
            self.console.print()

        # Default to N (safe option) for destructive actions
        proceed = Confirm.ask("Proceed?", default=False)

        if not proceed:
            new_instructions = Prompt.ask("What would you like to do instead?")
            return InterventionResponse(continue_execution=True, new_instructions=new_instructions)

        return InterventionResponse(continue_execution=True)

    def handle_stuck(self, context: InterventionContext) -> InterventionResponse:
        """Handle agent stuck intervention.

        Args:
            context: Intervention context

        Returns:
            User's response
        """
        self._ring_bell()
        self.console.print()
        if context.message:
            self.console.print(context.message)

        self.console.print("This might mean:")
        self.console.print("  - The page layout has changed")
        self.console.print("  - The element is hidden or not yet loaded")
        self.console.print("  - I'm looking in the wrong place")
        self.console.print()
        self.console.print("What would you like to do?")
        self.console.print("  1. Retry (I'll try again)")
        self.console.print("  2. Describe what you see (I'll tell you what's on the page)")
        self.console.print("  3. Give me new instructions")
        self.console.print("  4. Abort task")
        self.console.print()

        choice_str = Prompt.ask("Choose", default="1")

        try:
            choice = int(choice_str)
            if choice == 1:
                return InterventionResponse(continue_execution=True)
            elif choice == 2:
                # TODO: Implement page description
                self.console.print("[yellow]Page description not yet implemented. Retrying instead.[/yellow]")
                return InterventionResponse(continue_execution=True)
            elif choice == 3:
                new_instructions = Prompt.ask("What should I do instead?")
                return InterventionResponse(continue_execution=True, new_instructions=new_instructions)
            elif choice == 4:
                return InterventionResponse(continue_execution=False)
            else:
                self.console.print("[yellow]Invalid choice. Retrying.[/yellow]")
                return InterventionResponse(continue_execution=True)
        except ValueError:
            self.console.print("[yellow]Invalid choice. Retrying.[/yellow]")
            return InterventionResponse(continue_execution=True)

    def handle_max_steps(self, context: InterventionContext) -> InterventionResponse:
        """Handle approaching max steps intervention.

        Args:
            context: Intervention context

        Returns:
            User's response
        """
        self._ring_bell()
        self.console.print()
        self.console.print(
            f"[yellow]⚠ Approaching step limit ({context.step_number}/{context.max_steps} steps used).[/yellow]"
        )
        self.console.print()
        self.console.print("What would you like to do?")
        new_limit = context.max_steps * 2
        self.console.print(f"  1. Continue (increase limit to {new_limit} steps)")
        self.console.print("  2. Wrap up and show results so far")
        self.console.print("  3. Stop now")
        self.console.print()

        choice_str = Prompt.ask("Choose", default="1")

        try:
            choice = int(choice_str)
            if choice == 1:
                return InterventionResponse(continue_execution=True, increase_steps=True)
            elif choice == 2:
                # Signal to agent to wrap up
                return InterventionResponse(
                    continue_execution=True,
                    new_instructions="Please wrap up and show results so far",
                )
            elif choice == 3:
                return InterventionResponse(continue_execution=False)
            else:
                self.console.print("[yellow]Invalid choice. Continuing.[/yellow]")
                return InterventionResponse(continue_execution=True, increase_steps=True)
        except ValueError:
            self.console.print("[yellow]Invalid choice. Continuing.[/yellow]")
            return InterventionResponse(continue_execution=True, increase_steps=True)

    def handle_checkpoint(self, context: InterventionContext) -> InterventionResponse:
        """Handle phase transition checkpoint intervention.

        Args:
            context: Intervention context

        Returns:
            User's response
        """
        self._ring_bell()
        self.console.print()
        if context.progress_summary:
            self.console.print(context.progress_summary)
            self.console.print()

        self.console.print("Continue with this approach, or adjust?")
        self.console.print("  1. Continue")
        self.console.print("  2. Adjust (give new instructions)")
        self.console.print("  3. Stop")
        self.console.print()

        choice_str = Prompt.ask("Choose", default="1")

        try:
            choice = int(choice_str)
            if choice == 1:
                return InterventionResponse(continue_execution=True)
            elif choice == 2:
                new_instructions = Prompt.ask("What should I do differently?")
                return InterventionResponse(continue_execution=True, new_instructions=new_instructions)
            elif choice == 3:
                return InterventionResponse(continue_execution=False)
            else:
                self.console.print("[yellow]Invalid choice. Continuing.[/yellow]")
                return InterventionResponse(continue_execution=True)
        except ValueError:
            self.console.print("[yellow]Invalid choice. Continuing.[/yellow]")
            return InterventionResponse(continue_execution=True)

    def handle_confidence(self, context: InterventionContext) -> InterventionResponse:
        """Handle low confidence intervention.

        Args:
            context: Intervention context

        Returns:
            User's response
        """
        self._ring_bell()
        self.console.print()
        if context.confidence_detail:
            self.console.print(context.confidence_detail)
            self.console.print()

        self.console.print("How would you like to proceed?")
        self.console.print("  1. Proceed anyway")
        self.console.print("  2. Give guidance")
        self.console.print("  3. Skip this step")
        self.console.print()

        choice_str = Prompt.ask("Choose", default="2")

        try:
            choice = int(choice_str)
            if choice == 1:
                return InterventionResponse(continue_execution=True)
            elif choice == 2:
                new_instructions = Prompt.ask("What guidance would you like to give?")
                return InterventionResponse(continue_execution=True, new_instructions=new_instructions)
            elif choice == 3:
                return InterventionResponse(
                    continue_execution=True,
                    new_instructions="Skip this step and move on to the next one",
                )
            else:
                self.console.print("[yellow]Invalid choice. Waiting for guidance.[/yellow]")
                new_instructions = Prompt.ask("What guidance would you like to give?")
                return InterventionResponse(continue_execution=True, new_instructions=new_instructions)
        except ValueError:
            self.console.print("[yellow]Invalid choice. Waiting for guidance.[/yellow]")
            new_instructions = Prompt.ask("What guidance would you like to give?")
            return InterventionResponse(continue_execution=True, new_instructions=new_instructions)

    def handle_sub_goal_complete(self, context: InterventionContext) -> InterventionResponse:
        """Handle sub-goal completion intervention.

        Args:
            context: Intervention context

        Returns:
            User's response
        """
        self._ring_bell()
        self.console.print()
        if context.progress_summary:
            self.console.print(context.progress_summary)
            self.console.print()

        self.console.print("What next?")
        self.console.print("  1. Continue to next step")
        self.console.print("  2. Give new directions")
        self.console.print("  3. That's enough, show results")
        self.console.print()

        choice_str = Prompt.ask("Choose", default="1")

        try:
            choice = int(choice_str)
            if choice == 1:
                return InterventionResponse(continue_execution=True)
            elif choice == 2:
                new_instructions = Prompt.ask("What should I do next?")
                return InterventionResponse(continue_execution=True, new_instructions=new_instructions)
            elif choice == 3:
                return InterventionResponse(continue_execution=False)
            else:
                self.console.print("[yellow]Invalid choice. Continuing.[/yellow]")
                return InterventionResponse(continue_execution=True)
        except ValueError:
            self.console.print("[yellow]Invalid choice. Continuing.[/yellow]")
            return InterventionResponse(continue_execution=True)

    def handle_intervention(self, context: InterventionContext) -> InterventionResponse:
        """Route intervention to appropriate handler.

        Args:
            context: Intervention context

        Returns:
            User's response
        """
        handlers = {
            InterventionType.AUTH: self.handle_auth,
            InterventionType.CAPTCHA: self.handle_captcha,
            InterventionType.CHOICE: self.handle_choice,
            InterventionType.CONFIRM: self.handle_confirm,
            InterventionType.STUCK: self.handle_stuck,
            InterventionType.MAX_STEPS: self.handle_max_steps,
            InterventionType.CHECKPOINT: self.handle_checkpoint,
            InterventionType.CONFIDENCE: self.handle_confidence,
            InterventionType.SUB_GOAL_COMPLETE: self.handle_sub_goal_complete,
        }

        handler = handlers.get(context.intervention_type)
        if handler:
            return handler(context)

        # Unknown intervention type - default to continue
        self.console.print(f"[yellow]Unknown intervention type: {context.intervention_type}[/yellow]")
        return InterventionResponse(continue_execution=True)
