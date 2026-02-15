"""Output formatting for browser automation results."""

import json

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


class ResultFormatter:
    """Formats agent results for terminal display."""

    def __init__(self, console: Console):
        """Initialise the result formatter.

        Args:
            console: Rich console for output
        """
        self.console = console

    def format_time(self, seconds: float) -> str:
        """Format elapsed time as human-readable string.

        Args:
            seconds: Elapsed time in seconds

        Returns:
            Formatted time string (e.g., "1m 23s" or "45.2s")
        """
        if seconds < 60:
            return f"{seconds:.1f}s"
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes}m {remaining_seconds}s"

    def show_success(
        self,
        steps: int,
        elapsed: float,
        result_data: dict[str, str] | None = None,
        verbose: bool = False,
        actions_log: list[str] | None = None,
    ) -> None:
        """Display successful completion summary.

        Args:
            steps: Number of steps completed
            elapsed: Elapsed time in seconds
            result_data: Structured result data to display
            verbose: Whether to show the actions log
            actions_log: List of action descriptions from the task
        """
        time_str = self.format_time(elapsed)
        self.console.print()
        self.console.print(f"[green]✓ Task completed in {steps} steps ({time_str})[/green]")
        self.console.print()

        if result_data:
            self.console.print("Results:")
            for key, value in result_data.items():
                self.console.print(f"  {key}: {value}")

        if verbose and actions_log:
            self.console.print()
            self.console.print("Actions taken:")
            for i, action in enumerate(actions_log, 1):
                self.console.print(f"  {i}. {action}")

    def show_partial(
        self,
        steps: int,
        max_steps: int,
        reason: str,
        result_data: dict[str, str] | None = None,
        verbose: bool = False,
        actions_log: list[str] | None = None,
    ) -> None:
        """Display partial completion summary.

        Args:
            steps: Number of steps completed
            max_steps: Maximum steps allowed
            reason: Explanation of why task wasn't fully completed
            result_data: Partial result data to display
            verbose: Whether to show the actions log
            actions_log: List of action descriptions from the task
        """
        self.console.print()
        self.console.print(f"[yellow]⚠ Task partially completed (stopped at step {steps}/{max_steps})[/yellow]")
        self.console.print()
        self.console.print(reason)
        self.console.print()

        if result_data:
            for key, value in result_data.items():
                self.console.print(f"  {key}: {value}")

        if verbose and actions_log:
            self.console.print()
            self.console.print("Actions taken:")
            for i, action in enumerate(actions_log, 1):
                self.console.print(f"  {i}. {action}")

    def show_table(self, headers: list[str], rows: list[list[str]], title: str | None = None) -> None:
        """Display structured data as a table.

        Args:
            headers: Column headers
            rows: Table rows (max 5 rows shown)
            title: Optional table title
        """
        table = Table(title=title, show_header=True, header_style="bold")

        for header in headers:
            table.add_column(header)

        # Limit to 5 rows
        display_rows = rows[:5]
        for row in display_rows:
            table.add_row(*row)

        if len(rows) > 5:
            self.console.print()
            self.console.print(f"Showing 5 of {len(rows)} results")

        self.console.print()
        self.console.print(table)

    def show_error(self, error_message: str, suggestions: list[str] | None = None) -> None:
        """Display error message with optional suggestions.

        Args:
            error_message: Error message to display
            suggestions: Optional list of suggestions
        """
        self.console.print()
        self.console.print(f"[red]{error_message}[/red]")

        if suggestions:
            self.console.print()
            for suggestion in suggestions:
                self.console.print(f"  - {suggestion}")

        self.console.print()

    def show_completion_options(self, partial: bool = False) -> str:
        """Show next action options after task completion.

        Args:
            partial: Whether this was a partial completion

        Returns:
            User's choice as a string
        """
        from rich.prompt import Prompt

        self.console.print()
        self.console.print("What would you like to do next?")

        if partial:
            self.console.print("  1. Refine the search")
            self.console.print("  2. New task")
            self.console.print("  3. Export session summary")
            self.console.print("  4. Exit")
            default = "4"
        else:
            self.console.print("  1. New task")
            self.console.print("  2. Export session summary")
            self.console.print("  3. Exit")
            default = "3"

        self.console.print()
        choice = Prompt.ask("Choose", default=default)
        return choice

    def show_json_result(
        self,
        summary: str,
        structured_data: dict[str, str],
        steps: int,
        elapsed: float,
        success: bool,
    ) -> None:
        """Output task result as JSON to stdout.

        Args:
            summary: Task summary text
            structured_data: Key-value findings
            steps: Number of steps completed
            elapsed: Elapsed time in seconds
            success: Whether the task completed successfully
        """
        data = {
            "summary": summary,
            "data": structured_data,
            "steps": steps,
            "elapsed": elapsed,
            "success": success,
        }
        print(json.dumps(data, indent=2))

    def show_export_prompt(self, filepath: str) -> None:
        """Display confirmation that a session summary was exported.

        Args:
            filepath: Path where the summary was saved
        """
        self.console.print(f"[green]Session summary exported to: {filepath}[/green]")

    def show_session_summary(self, session_markdown: str) -> None:
        """Display a session summary in a Rich panel.

        Args:
            session_markdown: Markdown content of the session summary
        """
        panel = Panel(session_markdown, title="Session Summary", border_style="blue")
        self.console.print()
        self.console.print(panel)

    def show_panel(self, content: str, title: str | None = None, style: str = "blue") -> None:
        """Display content in a panel.

        Args:
            content: Panel content
            title: Optional panel title
            style: Panel border style/colour
        """
        panel = Panel(content, title=title, border_style=style)
        self.console.print()
        self.console.print(panel)
