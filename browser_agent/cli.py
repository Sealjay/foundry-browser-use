"""Interactive CLI for browser automation."""

import asyncio
import contextlib
import sys

from langchain_core.messages import HumanMessage
from prompt_toolkit import PromptSession
from prompt_toolkit.input import create_input
from prompt_toolkit.patch_stdout import patch_stdout
from rich.console import Console
from rich.prompt import Confirm, Prompt

from browser_agent.display import ResultFormatter
from browser_agent.intervention import InterventionHandler
from browser_agent.keyboard import AgentState, KeyHandler, build_toolbar
from browser_agent.runner import AgentConfig, AgentRunner
from browser_agent.session import Session, TaskRecord


class BrowserCLI:
    """Main CLI orchestrator for browser automation."""

    def __init__(self, verbose: bool = False):
        """Initialise the CLI.

        Args:
            verbose: Whether to show detailed agent actions
        """
        self.console = Console()
        self.session = Session(verbose=verbose)
        self.state = AgentState(verbose=verbose)
        self.key_handler = KeyHandler(self.state, self.console)
        self.prompt_session: PromptSession[str] = PromptSession(
            bottom_toolbar=lambda: build_toolbar(self.state),
        )
        self.formatter = ResultFormatter(self.console)
        self.intervention_handler = InterventionHandler(self.console, state=self.state)
        self.runner = AgentRunner(self.console, self.intervention_handler, session=self.session, state=self.state)

    def show_greeting(self) -> None:
        """Show initial greeting."""
        self.console.print("Browse - AI browser automation")
        self.console.print()

    async def get_task(self) -> str | None:
        """Get task from user.

        Returns:
            Task description or None if user cancels
        """
        try:
            task = await self.prompt_session.prompt_async("What would you like to do?\n> ")
        except (EOFError, KeyboardInterrupt):
            return None

        if not task or task.strip() == "":
            return None

        return task.strip()

    def confirm_task(self, task: str) -> tuple[bool, str]:
        """Confirm task understanding with user.

        If prior tasks exist in the session, context is included so
        follow-up references like "compare those" make sense.

        Args:
            task: Original task description

        Returns:
            Tuple of (confirmed, task_description)
        """
        self.console.print()
        if self.session.records:
            prior_count = len(self.session.records)
            last_summary = self.session.records[-1].summary or self.session.records[-1].task
            self.console.print(f"(Following on from {prior_count} prior task(s); last: {last_summary})")
        self.console.print(f"I'll {task.lower()}")
        self.console.print()

        confirmed = Confirm.ask("Is this correct?", default=True)

        if not confirmed:
            new_task = Prompt.ask("What would you like to do instead?")
            if new_task and new_task.strip():
                return self.confirm_task(new_task.strip())
            return False, task

        return True, task

    async def _ask_upfront_questions(self, task: str, context: str) -> str:
        """Ask clarifying questions before starting the agent.

        Makes one LLM call to generate 0-3 clarifying questions. If the
        task is clear enough, the agent starts immediately.

        Args:
            task: The user's task description
            context: Session context from prior tasks

        Returns:
            Updated task description with answers appended, or the
            original task if no questions were generated.
        """
        try:
            llm = self.runner._load_config()
        except ValueError:
            # No LLM configured yet - skip upfront questions
            return task

        prompt = (
            "Given this browser task, generate 0-3 brief clarifying questions that would help "
            "complete it accurately. If the task is clear enough, return NONE.\n\n"
            "Format: one question per line, numbered. Or just NONE.\n\n"
            f"Task: {task}\n"
            f"Context: {context or '(first task in session)'}"
        )

        try:
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            text = response.content if hasattr(response, "content") else str(response)

            if "NONE" in text.upper() or not text.strip():
                return task

            # Parse questions from response
            questions = [line.strip() for line in text.strip().split("\n") if line.strip()]
            if not questions:
                return task

            # Show questions and collect answers
            self.console.print()
            self.console.print("A few quick questions before we start:")
            self.console.print()
            answers = []
            for question in questions[:3]:
                self.console.print(f"  {question}")
                answer = Prompt.ask("  Answer", default="skip")
                if answer.lower() != "skip":
                    answers.append(f"Q: {question} A: {answer}")

            if answers:
                return task + "\n\nAdditional context:\n" + "\n".join(answers)
            return task

        except Exception:
            # If the upfront questions call fails, just proceed without them
            return task

    async def _run_key_listener(self) -> None:
        """Listen for keypresses during agent execution and dispatch to key handler."""
        inp = create_input()

        while self.state.running:
            # Enter raw mode to capture single keypresses
            with inp.raw_mode():
                loop = asyncio.get_running_loop()
                key_available = asyncio.Event()

                def _reader_callback(_event: asyncio.Event = key_available) -> None:
                    _event.set()

                loop.add_reader(inp.fileno(), _reader_callback)
                try:
                    while self.state.running:
                        key_available.clear()
                        try:
                            await asyncio.wait_for(key_available.wait(), timeout=0.1)
                        except TimeoutError:
                            continue

                        for kp in inp.read_keys():
                            self.key_handler.handle_key(kp.data)

                        # 'i' was pressed - leave raw mode to prompt for instruction
                        if self.state.paused and self.state.pending_instruction is None:
                            break
                finally:
                    loop.remove_reader(inp.fileno())

            # Outside raw mode - handle instruction prompt if 'i' triggered pause
            if self.state.running and self.state.paused and self.state.pending_instruction is None:
                try:
                    instruction = await self.prompt_session.prompt_async("Instruction> ")
                    if instruction and instruction.strip():
                        self.state.pending_instruction = instruction.strip()
                except (EOFError, KeyboardInterrupt):
                    pass
                self.state.paused = False

    async def run_task(
        self, task: str, context_prompt: str = ""
    ) -> tuple[bool, str | None, int, float, str, dict[str, str], list[str]]:
        """Run the browser automation task.

        Args:
            task: Task description
            context_prompt: Session context to prepend to the task

        Returns:
            Tuple of (success, result, steps, elapsed, summary, structured_data, actions_log)
        """
        config = AgentConfig(task=task, max_steps=25, use_vision=False, context_prompt=context_prompt)

        self.state.running = True
        self.state.quit_requested = False
        listener_task = asyncio.create_task(self._run_key_listener())

        try:
            result = await self.runner.run(config)
        except KeyboardInterrupt:
            self.console.print()
            self.console.print("[yellow]Task interrupted by user[/yellow]")
            result = (False, None, self.runner.current_step, 0.0, "", {}, [])
        finally:
            self.state.running = False
            listener_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await listener_task

        return result

    def show_results(
        self,
        success: bool,
        result: str | None,
        steps: int,
        elapsed: float,
        summary: str = "",
        structured_data: dict[str, str] | None = None,
        actions_log: list[str] | None = None,
    ) -> None:
        """Display task results.

        Args:
            success: Whether task completed successfully
            result: Result text from agent
            steps: Number of steps taken
            elapsed: Elapsed time in seconds
            summary: LLM-generated summary
            structured_data: Key-value findings
            actions_log: List of action descriptions
        """
        # Prefer summary over raw result for display
        display_data: dict[str, str] = {}
        if summary:
            display_data["Summary"] = summary
        if structured_data:
            display_data.update(structured_data)
        if not display_data and result:
            display_data["Result"] = result

        if success and (result or summary):
            self.formatter.show_success(
                steps, elapsed, display_data or None, verbose=self.session.verbose, actions_log=actions_log
            )
        elif steps > 0:
            reason = "The task was interrupted before completion."
            partial_data = display_data or ({"Partial result": result} if result else None)
            self.formatter.show_partial(
                steps,
                self.runner.max_steps,
                reason,
                partial_data,
                verbose=self.session.verbose,
                actions_log=actions_log,
            )
        else:
            self.formatter.show_error("Task could not be started. Please check your configuration.")

    def _handle_export(self) -> None:
        """Export the session summary to display and disk."""
        markdown = self.session.export_summary()
        self.formatter.show_session_summary(markdown)
        filepath = self.session.save_to_disk()
        self.formatter.show_export_prompt(filepath)

    def get_next_action(self, partial: bool = False) -> str:
        """Get next action from user after task completion.

        Args:
            partial: Whether the previous task was partially completed

        Returns:
            User's choice as a string
        """
        return self.formatter.show_completion_options(partial=partial)

    async def run_interactive_loop(self) -> None:
        """Run the main interactive loop."""
        self.show_greeting()

        # Ask about verbose mode if not already set via CLI flag
        if not self.session.verbose:
            verbose_choice = Confirm.ask("Verbose mode? (shows detailed agent actions)", default=False)
            self.session.verbose = verbose_choice

        # Sync keyboard state with session verbose setting
        self.state.verbose = self.session.verbose

        refine_task: str | None = None

        with patch_stdout():
            while True:
                # Get task from user (pre-populate with previous task if refining)
                if refine_task:
                    self.console.print()
                    self.console.print(f"Previous task: {refine_task}")
                    refinement = Prompt.ask("How would you like to refine this?", default="")
                    task = f"{refine_task} - refined: {refinement.strip()}" if refinement.strip() else refine_task
                    refine_task = None
                else:
                    task = await self.get_task()

                if not task:
                    self.console.print("Goodbye!")
                    break

                # Confirm task
                confirmed, final_task = self.confirm_task(task)
                if not confirmed:
                    continue

                # Build session context for this task
                context_prompt = self.session.build_context_prompt()

                # Ask upfront clarifying questions
                final_task = await self._ask_upfront_questions(final_task, context_prompt)

                # Run task
                success, result, steps, elapsed, summary, structured_data, actions_log = await self.run_task(
                    final_task, context_prompt=context_prompt
                )

                # Record task in session
                record = TaskRecord(
                    task=final_task,
                    summary=summary,
                    structured_data=structured_data,
                    steps_taken=steps,
                    elapsed=elapsed,
                    success=success,
                    actions_log=actions_log,
                )
                self.session.add_record(record)

                # Show results
                self.show_results(success, result, steps, elapsed, summary, structured_data, actions_log)

                # Completion menu loop (export returns here)
                while True:
                    next_action = self.get_next_action(partial=not success)

                    if not success:
                        # Partial menu: 1=refine, 2=new task, 3=export, 4=exit
                        if next_action == "1":
                            refine_task = final_task  # Carry forward for refinement
                            break
                        elif next_action == "2":
                            break  # New task - back to main loop
                        elif next_action == "3":
                            self._handle_export()
                            continue  # Show menu again
                        elif next_action == "4":
                            self.console.print()
                            self.console.print("Goodbye!")
                            return
                        else:
                            break  # Unknown - back to main loop
                    else:
                        # Success menu: 1=new task, 2=export, 3=exit
                        if next_action == "1":
                            break  # New task - back to main loop
                        elif next_action == "2":
                            self._handle_export()
                            continue  # Show menu again
                        elif next_action == "3":
                            self.console.print()
                            self.console.print("Goodbye!")
                            return
                        else:
                            break  # Unknown - back to main loop


async def run_cli(verbose: bool = False) -> None:
    """Run the CLI application.

    Args:
        verbose: Whether to enable verbose output mode
    """
    cli = BrowserCLI(verbose=verbose)

    try:
        await cli.run_interactive_loop()
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        cli.console.print()
        cli.console.print("Goodbye!")
        sys.exit(0)
    except Exception:
        # Handle unexpected errors
        cli.console.print()
        cli.console.print("[red]An unexpected error occurred. This has been logged for debugging.[/red]")
        cli.console.print()
        cli.console.print(
            "If this persists, please report it as an issue:\nhttps://github.com/Sealjay/foundry-browser-use/issues"
        )
        cli.console.print()
        import traceback

        print("Error details:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Entry point for the CLI."""
    asyncio.run(run_cli())
