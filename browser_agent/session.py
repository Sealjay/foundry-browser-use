"""Session management for multi-turn browser automation."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class TaskRecord:
    """Record of a single completed browser automation task."""

    task: str
    summary: str = ""
    structured_data: dict[str, str] = field(default_factory=dict)
    steps_taken: int = 0
    elapsed: float = 0.0
    success: bool = False
    actions_log: list[str] = field(default_factory=list)


class Session:
    """Tracks tasks within a multi-turn browsing session.

    Maintains a list of task records and provides context injection
    for follow-up tasks, so the agent understands prior results.
    """

    def __init__(self, verbose: bool = False):
        """Initialise a new session.

        Args:
            verbose: Whether to include full action logs in output
        """
        self.records: list[TaskRecord] = []
        self.verbose: bool = verbose

    def add_record(self, record: TaskRecord) -> None:
        """Append a completed task record to the session."""
        self.records.append(record)

    def build_context_prompt(self) -> str:
        """Generate context from prior task summaries for the next task.

        Last 5 summaries are included in full. Earlier tasks are condensed
        to a single line each. Returns an empty string if there are no
        prior tasks.
        """
        if not self.records:
            return ""

        lines = ["Context from this session:"]

        # Split into earlier (condensed) and recent (full) groups
        if len(self.records) > 5:
            earlier = self.records[:-5]
            recent = self.records[-5:]

            for i, record in enumerate(earlier, start=1):
                # Condensed: just the task name and success/failure
                status = "completed" if record.success else "failed"
                lines.append(f"- Task {i}: {record.task} ({status})")

            offset = len(earlier)
        else:
            recent = self.records
            offset = 0

        for i, record in enumerate(recent, start=offset + 1):
            summary = record.summary or "No summary available"
            lines.append(f"- Task {i}: {summary}")

        return "\n".join(lines)

    def export_summary(self) -> str:
        """Export the full session as a self-contained markdown document.

        Includes all tasks, summaries, structured data, and a suggested
        follow-up prompt for continuing the work elsewhere.
        """
        parts = ["# Browser Session Summary\n"]

        for i, record in enumerate(self.records, start=1):
            status = "Completed" if record.success else "Failed"
            parts.append(f"## Task {i}: {record.task}\n")
            parts.append(f"**Status:** {status}  ")
            parts.append(f"**Steps:** {record.steps_taken}  ")
            parts.append(f"**Time:** {record.elapsed:.1f}s\n")

            if record.summary:
                parts.append(f"**Summary:** {record.summary}\n")

            if record.structured_data:
                parts.append("**Findings:**\n")
                for key, value in record.structured_data.items():
                    parts.append(f"- **{key}:** {value}")
                parts.append("")

            if self.verbose and record.actions_log:
                parts.append("<details>\n<summary>Actions log</summary>\n")
                for action in record.actions_log:
                    parts.append(f"1. {action}")
                parts.append("\n</details>\n")

        # Suggested follow-up prompt
        parts.append("---\n")
        parts.append("## Suggested follow-up\n")
        parts.append("Use the summaries above as context for your next step. For example:\n")
        parts.append("> Based on the session above, please analyse the findings and suggest next actions.\n")

        return "\n".join(parts)

    def save_to_disk(self, path: str | None = None) -> str:
        """Write the session export to a markdown file.

        Args:
            path: File path to write to. If None, generates a default
                  filename based on the current timestamp.

        Returns:
            The path that was written to.
        """
        if path is None:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            path = f"logs/browse-session-{timestamp}.md"

        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(self.export_summary(), encoding="utf-8")
        return str(output)
