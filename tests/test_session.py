"""Tests for session management and context building."""

import os
import tempfile

from browser_agent.session import Session, TaskRecord


def test_empty_session_no_context(session: Session) -> None:
    """Empty session returns empty context string."""
    assert session.build_context_prompt() == ""


def test_single_record_context(session: Session, sample_task_record: TaskRecord) -> None:
    """Single record produces a context string."""
    session.add_record(sample_task_record)
    context = session.build_context_prompt()
    assert "Context from this session:" in context
    assert "Task 1:" in context


def test_context_cap_at_five(session: Session) -> None:
    """With 7 records, first 2 are condensed and last 5 are full."""
    for i in range(7):
        record = TaskRecord(
            task=f"Task number {i}",
            summary=f"Summary for task {i}",
            success=i % 2 == 0,
            steps_taken=i + 1,
        )
        session.add_record(record)

    context = session.build_context_prompt()
    # First 2 should be condensed (just task name + status)
    assert "Task number 0 (completed)" in context
    assert "Task number 1 (failed)" in context
    # Last 5 should have full summaries
    assert "Summary for task 2" in context
    assert "Summary for task 6" in context


def test_export_contains_all_tasks(session: Session, sample_task_record: TaskRecord) -> None:
    """Export markdown includes all task summaries."""
    session.add_record(sample_task_record)
    second = TaskRecord(task="Compare prices", summary="Price comparison done", success=True)
    session.add_record(second)

    markdown = session.export_summary()
    assert "Task 1:" in markdown
    assert "Task 2:" in markdown
    assert "Logitech K380" in markdown
    assert "Price comparison done" in markdown
    assert "Suggested follow-up" in markdown


def test_save_to_disk(session: Session, sample_task_record: TaskRecord) -> None:
    """Session saves to disk at specified path."""
    session.add_record(sample_task_record)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test-session.md")
        result_path = session.save_to_disk(path)
        assert os.path.exists(result_path)
        with open(result_path) as f:
            content = f.read()
        assert "Browser Session Summary" in content


def test_add_record_appends(session: Session) -> None:
    """Records list grows when records are added."""
    assert len(session.records) == 0
    session.add_record(TaskRecord(task="Test"))
    assert len(session.records) == 1
    session.add_record(TaskRecord(task="Test 2"))
    assert len(session.records) == 2
