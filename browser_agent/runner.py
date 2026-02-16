"""Browser automation agent execution wrapper."""

import asyncio
import json
import os
import platform
import time
from dataclasses import dataclass

from browser_use import Agent, ChatAzureOpenAI
from browser_use.browser.profile import BrowserProfile
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from rich.console import Console

from browser_agent.intervention import (
    InterventionContext,
    InterventionHandler,
    InterventionResponse,
    InterventionType,
)
from browser_agent.keyboard import AgentState, FooterManager
from browser_agent.session import Session

STRATEGY_VARIATION_PROMPT = (
    "\n\nIMPORTANT - Avoid repeating failed approaches:\n"
    "If an extraction or interaction attempt does not produce useful results after "
    "2 tries, you MUST switch to a fundamentally different strategy. Do not rephrase "
    "the same selector or approach. Instead try one of these alternatives:\n"
    "- Use broader CSS selectors (e.g. article, section, main) instead of specific attributes\n"
    "- Extract raw text via document.body.innerText or textContent\n"
    "- Use link text and heading elements (h1, h2, h3, a) to identify content\n"
    "- Scroll the page and look for dynamically loaded content\n"
    "- Try the accessibility tree to find semantic page structure\n"
    "Each retry must be a genuinely different approach, not a minor variation."
)


@dataclass
class AgentConfig:
    """Configuration for the browser automation agent."""

    task: str
    max_steps: int = 25
    use_vision: bool = False
    context_prompt: str = ""


class AgentRunner:
    """Wraps Browser Use Agent with callbacks and intervention handling."""

    def __init__(
        self,
        console: Console,
        intervention_handler: InterventionHandler,
        session: Session | None = None,
        state: AgentState | None = None,
        footer: FooterManager | None = None,
    ):
        """Initialise the agent runner.

        Args:
            console: Rich console for output
            intervention_handler: Handler for human interventions
            session: Optional session for multi-turn context
            state: Optional shared state for keyboard-driven control
            footer: Optional persistent footer for shortcut bar display
        """
        self.console = console
        self.intervention_handler = intervention_handler
        self.session = session
        self.state = state
        self.footer = footer
        self.current_step = 0
        self.max_steps = 25
        self.start_time = 0.0
        self.consecutive_failures = 0
        self.step_times: dict[int, float] = {}
        self.actions_log: list[str] = []
        self._last_phase: str = ""
        self._last_checkpoint_step: int = 0
        self._last_subgoal_step: int = 0
        self._repetition_warnings: int = 0
        self._last_browser_visible: bool = False
        self._agent: Agent | None = None
        self._browser_window_id: int | None = None
        self._browser_app_name: str | None = None
        self._vision_suggested: bool = False

    def _run_intervention(self, context: InterventionContext) -> InterventionResponse:
        """Run an intervention with footer suspended and raw mode released.

        Sets intervention_active so the key listener exits raw mode,
        suspends the footer so prompts render normally, then restores both.
        """
        if self.state:
            self.state.intervention_active = True
        if self.footer:
            self.footer.stop()

        try:
            return self.intervention_handler.handle_intervention(context)
        finally:
            if self.footer:
                self.footer.start()
            if self.state:
                self.state.intervention_active = False

    async def _get_browser_window_id(self) -> int | None:
        """Get the CDP window ID for the browser, caching after first call."""
        if self._browser_window_id is not None:
            return self._browser_window_id

        if not self._agent:
            return None

        try:
            cdp_client = self._agent.browser_session.cdp_client
            # The root CDP client requires a targetId - find a page target first
            targets = await cdp_client.send.Target.getTargets()
            target_id = None
            for t in targets.get("targetInfos", []):
                if t.get("type") == "page":
                    target_id = t["targetId"]
                    break

            if target_id is None:
                return None

            result = await cdp_client.send.Browser.getWindowForTarget({"targetId": target_id})
            self._browser_window_id = result["windowId"]
            return self._browser_window_id
        except Exception:
            return None

    def _get_browser_app_name(self) -> str | None:
        """Get the macOS .app bundle name for the browser process.

        Returns the cached name on subsequent calls. Returns None on non-Darwin platforms.
        """
        if platform.system() != "Darwin":
            return None

        if self._browser_app_name is not None:
            return self._browser_app_name

        try:
            exe_path: str = self._agent.browser_session.browser.contexts[  # type: ignore[union-attr]
                0
            ]._impl_obj._browser._connection._transport._process.args[0]
            from pathlib import PurePosixPath

            parts = PurePosixPath(exe_path).parts
            for part in parts:
                if part.endswith(".app"):
                    self._browser_app_name = part[: -len(".app")]
                    return self._browser_app_name
        except Exception:
            pass

        # Fallback for Chromium-based testing browsers on macOS
        self._browser_app_name = "Google Chrome for Testing"
        return self._browser_app_name

    async def _hide_browser_macos(self, app_name: str) -> bool:
        """Hide the browser via osascript (macOS only). Returns True on success."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "osascript",
                "-e",
                f'tell application "System Events" to set visible of process "{app_name}" to false',
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=3.0)
            return proc.returncode == 0
        except Exception:
            return False

    async def _show_browser_macos(self, app_name: str) -> bool:
        """Show/activate the browser via osascript (macOS only). Returns True on success."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "osascript",
                "-e",
                f'tell application "{app_name}" to activate',
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=3.0)
            return proc.returncode == 0
        except Exception:
            return False

    async def _minimize_browser(self) -> None:
        """Minimise the browser window. Uses osascript on macOS, CDP elsewhere."""
        if platform.system() == "Darwin":
            app_name = self._get_browser_app_name()
            if app_name and await self._hide_browser_macos(app_name):
                return

        # CDP fallback
        window_id = await self._get_browser_window_id()
        if window_id is None:
            return
        try:
            cdp_client = self._agent.browser_session.cdp_client  # type: ignore[union-attr]
            await cdp_client.send.Browser.setWindowBounds(
                {"windowId": window_id, "bounds": {"windowState": "minimized"}}
            )
        except Exception:
            pass

    async def _restore_browser(self) -> None:
        """Restore the browser window. Uses osascript on macOS, CDP elsewhere."""
        if platform.system() == "Darwin":
            app_name = self._get_browser_app_name()
            if app_name and await self._show_browser_macos(app_name):
                return

        # CDP fallback
        window_id = await self._get_browser_window_id()
        if window_id is None:
            return
        try:
            cdp_client = self._agent.browser_session.cdp_client  # type: ignore[union-attr]
            await cdp_client.send.Browser.setWindowBounds({"windowId": window_id, "bounds": {"windowState": "normal"}})
        except Exception:
            pass

    async def toggle_browser_immediate(self) -> None:
        """Toggle browser visibility immediately (called from keypress callback)."""
        if not self._agent:
            return
        if self.state and self.state.browser_visible:
            await self._restore_browser()
        else:
            await self._minimize_browser()
        if self.state:
            self._last_browser_visible = self.state.browser_visible

    def _load_config(self) -> ChatAzureOpenAI:
        """Load Azure OpenAI configuration from environment.

        Returns:
            Configured ChatAzureOpenAI instance

        Raises:
            ValueError: If required environment variables are missing
        """
        load_dotenv()

        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION")

        if not endpoint:
            raise ValueError(
                "AZURE_OPENAI_ENDPOINT not found in environment.\n"
                "Please set the required environment variables in .env or your shell.\n\n"
                "See .env.example for the full list of required variables."
            )

        if not api_key:
            raise ValueError(
                "AZURE_OPENAI_API_KEY not found in environment.\n"
                "Please set the required environment variables in .env or your shell.\n\n"
                "See .env.example for the full list of required variables."
            )

        # ChatAzureOpenAI from browser_use reads AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY
        # automatically from environment. For Responses API (GPT-5.1 Codex models), set
        # AZURE_OPENAI_API_VERSION to 2025-03-01-preview or later.
        model_config = {"model": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-41-mini")}

        # Pass api_version only if explicitly set (optional for most deployments)
        if api_version:
            model_config["api_version"] = api_version

        return ChatAzureOpenAI(**model_config)  # type: ignore[arg-type]  # pydantic coerces string values from env vars at runtime

    def _format_step_status(self, step_number: int, description: str, elapsed: float | None = None) -> str:
        """Format step status line.

        Args:
            step_number: Current step number
            description: Plain English description of step
            elapsed: Elapsed time for this step in seconds

        Returns:
            Formatted status line
        """
        status = f"Step {step_number}/{self.max_steps}: {description}"
        if elapsed and elapsed > 1.0:
            status += f" ({elapsed:.1f}s)"
        return status

    def _get_action_description(self, agent_output) -> str:
        """Extract plain English description from agent output.

        Args:
            agent_output: Agent output object

        Returns:
            Plain English description of the action
        """
        # Use next_goal for description if available
        if hasattr(agent_output, "next_goal") and agent_output.next_goal:
            return agent_output.next_goal

        # Fallback to action description if available
        if hasattr(agent_output, "action") and agent_output.action:
            actions = agent_output.action if isinstance(agent_output.action, list) else [agent_output.action]
            if actions:
                # Get first action description
                action = actions[0]
                if hasattr(action, "description") and action.description:
                    return action.description

        return "Processing"

    def _classify_phase(self, description: str) -> str:
        """Classify an action description into a phase by keyword matching.

        Args:
            description: Plain English description of the current goal

        Returns:
            Phase name or empty string if unclassified
        """
        text = description.lower()
        phase_keywords = {
            "searching": ["search", "find", "look", "browse", "navigate"],
            "comparing": ["compare", "evaluate", "review", "assess", "weigh"],
            "acting": ["click", "select", "choose", "submit", "fill", "type"],
            "extracting": ["extract", "read", "get", "copy", "scrape", "collect"],
        }
        for phase, keywords in phase_keywords.items():
            if any(kw in text for kw in keywords):
                return phase
        return ""

    def _detect_hedging(self, evaluation: str) -> bool:
        """Check whether the evaluation text contains hedging language.

        Args:
            evaluation: The evaluation_previous_goal text

        Returns:
            True if hedging is detected
        """
        hedging_terms = ["unsure", "uncertain", "might", "could be", "not certain", "unclear"]
        text = evaluation.lower()
        return any(term in text for term in hedging_terms)

    def _detect_completion(self, evaluation: str) -> bool:
        """Check whether the evaluation text indicates a sub-goal was completed.

        Args:
            evaluation: The evaluation_previous_goal text

        Returns:
            True if completion language is detected
        """
        completion_terms = ["completed", "found", "successfully", "done"]
        text = evaluation.lower()
        return any(term in text for term in completion_terms)

    def _check_for_failure(self, agent_output) -> bool:
        """Check if the previous step failed.

        Args:
            agent_output: Agent output object

        Returns:
            True if the step failed
        """
        if hasattr(agent_output, "evaluation_previous_goal"):
            evaluation = str(agent_output.evaluation_previous_goal).lower()
            return "failure" in evaluation or "failed" in evaluation
        return False

    def _word_similarity(self, a: str, b: str) -> float:
        """Compute word-level Jaccard similarity between two strings.

        Args:
            a: First string
            b: Second string

        Returns:
            Similarity score between 0.0 and 1.0
        """
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        return len(words_a & words_b) / len(words_a | words_b)

    def _detect_repetition(self, window: int = 3, threshold: float = 0.7) -> bool:
        """Check whether the last N action descriptions are repetitive.

        Args:
            window: Number of recent actions to compare
            threshold: Minimum Jaccard similarity to count as repetitive

        Returns:
            True if all pairs in the window exceed the threshold
        """
        if len(self.actions_log) < window:
            return False

        recent = self.actions_log[-window:]
        for i in range(len(recent)):
            for j in range(i + 1, len(recent)):
                if self._word_similarity(recent[i], recent[j]) < threshold:
                    return False
        return True

    async def _step_callback(self, _browser_state, agent_output, step_number: int) -> None:
        """Callback for each agent step.

        Args:
            _browser_state: Current browser state (unused; required by callback signature)
            agent_output: Agent output for this step
            step_number: Current step number
        """
        # --- Keyboard state checks (quit, pause, instruction, verbose sync) ---
        if self.state:
            if self.state.quit_requested:
                raise KeyboardInterrupt("User quit via keyboard")

            while self.state.paused and not self.state.quit_requested:
                await asyncio.sleep(0.1)
            if self.state.quit_requested:
                raise KeyboardInterrupt("User quit via keyboard")

            if self.state.pending_instruction:
                instruction = self.state.pending_instruction
                self.state.pending_instruction = None
                self.actions_log.append(f"[User instruction] {instruction}")
                self.console.print(f"[green]Instruction received: {instruction}[/green]")
                self.console.print("[dim]Note: mid-run instruction injection not yet supported by browser-use.[/dim]")

            if self.session and self.state.verbose != self.session.verbose:
                self.session.verbose = self.state.verbose

        # --- Browser visibility: toggle on change ---
        visibility_changed = self.state and self.state.browser_visible != self._last_browser_visible

        if self._agent and visibility_changed:
            if self.state and self.state.browser_visible:
                await self._restore_browser()
            else:
                await self._minimize_browser()
            if self.state:
                self._last_browser_visible = self.state.browser_visible

        self.current_step = step_number

        # Track step timing
        step_start = self.step_times.get(step_number, time.time())
        elapsed = time.time() - step_start

        # Check for failure
        if self._check_for_failure(agent_output):
            self.consecutive_failures += 1
        else:
            self.consecutive_failures = 0

        # Get action description
        description = self._get_action_description(agent_output)

        # Track actions log
        self.actions_log.append(description)

        # Format and display status
        status = self._format_step_status(step_number, description, elapsed)
        self.console.print(status)

        # Refresh persistent footer (or fall back to inline print)
        if self.footer:
            self.footer.refresh()
        elif self.state:
            browser_action = "Minimise" if self.state.browser_visible else "Show"
            verbose_action = "Less detail" if self.state.verbose else "More detail"
            vision_action = "Disable" if self.state.vision_enabled else "Enable"
            pause_action = "Resume" if self.state.paused else "Pause"
            shortcuts = (
                f"[B] {browser_action} browser  [V] {verbose_action}  [F] {vision_action} vision"
                f"  [I] Instruct  [P] {pause_action}  [Q] Quit"
            )
            self.console.print(f"  [cyan]{shortcuts}[/cyan]")

        # Store step start time for next iteration
        self.step_times[step_number + 1] = time.time()

        # --- Phase and evaluation-based intervention detection ---
        evaluation_text = ""
        if hasattr(agent_output, "evaluation_previous_goal") and agent_output.evaluation_previous_goal:
            evaluation_text = str(agent_output.evaluation_previous_goal)

        current_phase = self._classify_phase(description)
        phase_changed = current_phase and current_phase != self._last_phase and self._last_phase != ""
        if current_phase:
            self._last_phase = current_phase

        # Confidence intervention - hedging in evaluation
        if evaluation_text and self._detect_hedging(evaluation_text):
            context = InterventionContext(
                intervention_type=InterventionType.CONFIDENCE,
                step_number=step_number,
                max_steps=self.max_steps,
                confidence_detail=f"The agent seems uncertain: {evaluation_text}",
            )
            response = self._run_intervention(context)

            if not response.continue_execution:
                raise KeyboardInterrupt("User aborted at confidence check")
            if response.new_instructions:
                self.console.print("[yellow]New instructions received but not yet implemented[/yellow]")

        # Sub-goal complete intervention - completion language + phase change
        if (
            evaluation_text
            and self._detect_completion(evaluation_text)
            and phase_changed
            and (step_number - self._last_subgoal_step) >= 5
        ):
            self._last_subgoal_step = step_number
            actions_so_far = "; ".join(self.actions_log[-5:])
            context = InterventionContext(
                intervention_type=InterventionType.SUB_GOAL_COMPLETE,
                step_number=step_number,
                max_steps=self.max_steps,
                progress_summary=f"Sub-goal reached at step {step_number}. Recent actions: {actions_so_far}",
            )
            response = self._run_intervention(context)

            if not response.continue_execution:
                raise KeyboardInterrupt("User stopped at sub-goal")
            if response.new_instructions:
                self.console.print("[yellow]New instructions received but not yet implemented[/yellow]")

        # Checkpoint intervention - phase transition (without sub-goal, to avoid double-prompting)
        elif phase_changed and (step_number - self._last_checkpoint_step) >= 5:
            self._last_checkpoint_step = step_number
            actions_so_far = "; ".join(self.actions_log[-5:])
            context = InterventionContext(
                intervention_type=InterventionType.CHECKPOINT,
                step_number=step_number,
                max_steps=self.max_steps,
                progress_summary=(
                    f"Phase change detected at step {step_number} "
                    f"({self._last_phase}). Recent actions: {actions_so_far}"
                ),
            )
            response = self._run_intervention(context)

            if not response.continue_execution:
                raise KeyboardInterrupt("User stopped at checkpoint")
            if response.new_instructions:
                self.console.print("[yellow]New instructions received but not yet implemented[/yellow]")

        # Check for repetitive actions (agent retrying the same approach)
        if self._detect_repetition():
            self._repetition_warnings += 1
            if self._repetition_warnings == 1:
                # First warning - log to console so the user is aware
                self.console.print(
                    "[yellow]Repetitive actions detected - the agent appears to be retrying the same approach.[/yellow]"
                )
            elif self._repetition_warnings >= 2:
                # Escalate to human intervention
                context = InterventionContext(
                    intervention_type=InterventionType.STUCK,
                    step_number=step_number,
                    max_steps=self.max_steps,
                    message=(
                        "The agent has been repeating similar actions without progress. "
                        f"Recent actions: {'; '.join(self.actions_log[-3:])}"
                    ),
                )
                response = self._run_intervention(context)

                if not response.continue_execution:
                    raise KeyboardInterrupt("User aborted at repetition check")
                if response.new_instructions:
                    self.console.print("[yellow]New instructions received but not yet implemented[/yellow]")

                # Suggest vision mode if not already enabled and not yet suggested
                if self.state and not self.state.vision_enabled and not self._vision_suggested:
                    self.console.print("[cyan]Tip: Press [F] to enable vision mode for visually complex pages[/cyan]")
                    self._vision_suggested = True

                self._repetition_warnings = 0

        # Check for stuck condition (3 consecutive failures)
        if self.consecutive_failures >= 3:
            context = InterventionContext(
                intervention_type=InterventionType.STUCK,
                step_number=step_number,
                max_steps=self.max_steps,
                message=f"I tried to {description} but couldn't complete the action.",
            )
            response = self._run_intervention(context)

            if not response.continue_execution:
                raise KeyboardInterrupt("User aborted task")

            if response.new_instructions:
                self.console.print("[yellow]New instructions received but not yet implemented[/yellow]")

            # Suggest vision mode if not already enabled and not yet suggested
            if self.state and not self.state.vision_enabled and not self._vision_suggested:
                self.console.print("[cyan]Tip: Press [F] to enable vision mode for visually complex pages[/cyan]")
                self._vision_suggested = True

            # Reset failure counter after intervention
            self.consecutive_failures = 0

        # Check for approaching max steps (80% threshold)
        threshold = int(self.max_steps * 0.8)
        if step_number >= threshold and step_number == threshold:
            self.console.print(
                f"[yellow]⚠ Approaching step limit ({step_number}/{self.max_steps}). "
                f"Agent will prompt for guidance at step {threshold + 1}.[/yellow]"
            )

        # Prompt for action at threshold
        if step_number > threshold:
            context = InterventionContext(
                intervention_type=InterventionType.MAX_STEPS,
                step_number=step_number,
                max_steps=self.max_steps,
            )
            response = self._run_intervention(context)

            if not response.continue_execution:
                raise KeyboardInterrupt("User stopped task at step limit")

            if response.increase_steps:
                self.max_steps *= 2
                self.console.print(f"[green]Step limit increased to {self.max_steps}[/green]")

            if response.new_instructions:
                self.console.print("[yellow]Wrap up requested but not yet implemented[/yellow]")

    async def _done_callback(self, _history) -> None:
        """Callback when agent completes."""
        # The CLI layer will handle result display
        pass

    async def _generate_summary(
        self,
        llm: ChatAzureOpenAI,
        task: str,
        result_text: str | None,
    ) -> tuple[str, dict[str, str]]:
        """Generate a concise summary and structured data via an LLM call.

        Args:
            llm: The LLM instance to use for summarisation
            task: Original task description
            result_text: Final result text from the agent

        Returns:
            Tuple of (summary, structured_data)
        """
        actions_joined = "\n".join(f"- {a}" for a in self.actions_log) if self.actions_log else "(none)"
        prompt = (
            "Summarise the results of this browser automation task in 1-3 sentences. "
            "Also extract any structured key-value data (URLs, prices, names, dates) as a JSON object.\n\n"
            "Respond in this exact format:\n"
            "SUMMARY: <your summary>\n"
            "DATA: <JSON object or {}>\n\n"
            f"Task: {task}\n\n"
            f"Result: {result_text or '(no result)'}\n\n"
            f"Actions taken:\n{actions_joined}"
        )

        try:
            response = await llm.ainvoke([HumanMessage(content=prompt)])  # type: ignore[arg-type]  # HumanMessage is a BaseMessage subclass; Pylance can't resolve langchain's type hierarchy
            text = response.content if hasattr(response, "content") else str(response)  # type: ignore[union-attr]  # content exists on AIMessage at runtime

            # Parse SUMMARY and DATA from the response
            summary = ""
            structured_data: dict[str, str] = {}

            for line in text.split("\n"):
                if line.startswith("SUMMARY:"):
                    summary = line[len("SUMMARY:") :].strip()
                elif line.startswith("DATA:"):
                    raw_json = line[len("DATA:") :].strip()
                    try:
                        parsed = json.loads(raw_json)
                        if isinstance(parsed, dict):
                            structured_data = {str(k): str(v) for k, v in parsed.items()}
                    except (json.JSONDecodeError, ValueError):
                        pass

            # Fallback if parsing found nothing useful
            if not summary:
                summary = result_text or ""

            return summary, structured_data

        except Exception:
            # If the summary call fails, degrade gracefully
            return result_text or "", {}

    async def run(self, config: AgentConfig) -> tuple[bool, str | None, int, float, str, dict[str, str], list[str]]:
        """Run the browser automation agent.

        Args:
            config: Agent configuration

        Returns:
            Tuple of (success, result, steps_taken, elapsed_time,
                       summary, structured_data, actions_log)
        """
        try:
            # Reset per-run state (start_time first so exception handlers have a valid value)
            self.start_time = time.time()
            self.actions_log = []
            self._last_phase = ""
            self._last_checkpoint_step = 0
            self._last_subgoal_step = 0
            self.current_step = 0
            self.consecutive_failures = 0
            self._repetition_warnings = 0
            self.step_times = {}
            self._browser_window_id = None
            self._browser_app_name = None
            self._vision_suggested = False

            # Load Azure OpenAI configuration
            llm = self._load_config()

            # Set up agent config
            self.max_steps = config.max_steps
            self.step_times[1] = time.time()

            # Build full task with optional session context
            full_task = f"{config.context_prompt}\n\nNew task: {config.task}" if config.context_prompt else config.task

            # Start browser headed but minimise via CDP before agent steps begin.
            # window_position=None prevents the default --window-position=0,0 arg.
            # window_size prevents --start-maximized being added automatically.
            browser_profile = BrowserProfile(
                window_position=None,
                window_size={"width": 1280, "height": 900},  # type: ignore[arg-type]  # browser-use accepts plain dicts for ViewportSize
            )

            # Create agent with callbacks
            agent = Agent(
                task=full_task,
                llm=llm,
                browser_profile=browser_profile,
                max_steps=self.max_steps,
                use_vision=config.use_vision,
                register_new_step_callback=self._step_callback,
                register_done_callback=self._done_callback,
                extend_system_message=STRATEGY_VARIATION_PROMPT,
            )
            self._agent = agent

            # Pre-start browser and minimise immediately (before agent steps begin)
            self.console.print("Starting agent...")
            await agent.browser_session.start()
            if not (self.state and self.state.browser_visible):
                await self._minimize_browser()
            self.console.print()

            result = await agent.run()

            # Calculate metrics
            elapsed = time.time() - self.start_time
            steps_taken = self.current_step

            # Extract result text
            result_text = None
            if hasattr(result, "final_result") and callable(result.final_result):
                result_text = result.final_result()
            elif isinstance(result, str):
                result_text = result
            elif hasattr(result, "text"):
                result_text = result.text  # type: ignore[union-attr]  # guarded by hasattr check above

            # Generate summary via additional LLM call
            summary, structured_data = await self._generate_summary(llm, config.task, result_text)

            return True, result_text, steps_taken, elapsed, summary, structured_data, list(self.actions_log)

        except KeyboardInterrupt:
            # User interrupted execution
            elapsed = time.time() - self.start_time
            return False, None, self.current_step, elapsed, "", {}, list(self.actions_log)

        except Exception as e:
            # Handle errors
            elapsed = time.time() - self.start_time
            error_msg = self._format_error(e)
            self.console.print()
            self.console.print(f"[red]{error_msg}[/red]")
            self.console.print()
            return False, None, self.current_step, elapsed, "", {}, list(self.actions_log)

        finally:
            self._agent = None

    def _format_error(self, error: Exception) -> str:
        """Format error message for user display.

        Args:
            error: Exception that occurred

        Returns:
            User-friendly error message
        """
        error_str = str(error).lower()

        # Network errors
        if "network" in error_str or "connection" in error_str or "timeout" in error_str:
            return "Network error: Unable to connect. Please check your internet connection and try again."

        # Azure API errors - Authentication
        if "401" in error_str or "unauthorized" in error_str:
            return (
                "API error: Authentication failed. Please check your AZURE_OPENAI_API_KEY.\n\n"
                "If using Microsoft Entra ID, verify your token is scoped for "
                "https://cognitiveservices.azure.com/.default"
            )

        if "403" in error_str or "forbidden" in error_str:
            return (
                "API error: Access forbidden. Your API key or token doesn't have permission "
                "to access this resource.\n\n"
                "Check your Azure OpenAI deployment permissions and ensure your subscription "
                "has quota allocated."
            )

        # Rate limiting errors
        if "429" in error_str or "rate limit" in error_str:
            return (
                "API error: Rate limit exceeded. Your Azure OpenAI deployment is receiving too many requests.\n\n"
                "Azure returns a 'Retry-After' header indicating how long to wait before retrying.\n"
                "Consider implementing exponential backoff, or request a quota increase in the Azure portal.\n\n"
                "For high-volume workloads, consider upgrading to Provisioned Throughput Units (PTU) "
                "for guaranteed capacity and predictable latency."
            )

        # Service availability errors
        if "500" in error_str or "502" in error_str or "503" in error_str:
            return (
                "API error: Azure OpenAI service is temporarily unavailable. Please try again in a few moments.\n\n"
                "If this persists, check the Azure status page or try a different region."
            )

        # Deployment not found
        if "404" in error_str and "deployment" in error_str:
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "unknown")
            return (
                f"API error: Model deployment '{deployment}' not found.\n\n"
                "Please verify:\n"
                "- AZURE_OPENAI_DEPLOYMENT_NAME matches your deployment name in the Azure portal\n"
                "- The deployment exists in the region specified by AZURE_OPENAI_ENDPOINT\n"
                "- The model deployment is active and not in a failed state"
            )

        # Region/quota errors
        if "quota" in error_str or "capacity" in error_str:
            return (
                "API error: Insufficient quota or capacity in this region.\n\n"
                "To resolve this:\n"
                "1. Request a quota increase via the Azure portal\n"
                "2. Try deploying in a different region\n"
                "3. Check the regional capacity API to find available regions"
            )

        # API version errors (for Responses API)
        if "api" in error_str and "version" in error_str:
            return (
                "API error: Unsupported or invalid API version.\n\n"
                "For GPT-5.1 Codex models and Responses API, set AZURE_OPENAI_API_VERSION "
                "to 2025-03-01-preview or later in your .env file."
            )

        # Browser errors
        if "browser" in error_str or "playwright" in error_str:
            return (
                "Browser error: Browser process crashed or became unresponsive.\n"
                "This might be due to insufficient memory or website incompatibility.\n\n"
                "Please try again later or choose a different task."
            )

        # Generic error
        return "An unexpected error occurred. Please try again or report this issue if it persists."
