"""Tests for Rich TUI components and formatting."""

from pathlib import Path
import pytest

from xbot.config import Config
from xbot.tui.components import (
    create_banner,
    create_config_table,
    create_help_table,
    create_tool_call_panel,
    create_tool_result_panel,
    create_tools_table,
)
from xbot.tui.formatting import format_json, format_markdown, truncate_preview


def test_tui_components_render(tmp_path):
    """Test all Rich components can be instantiated without error."""
    cfg = Config(
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model_id="gpt-4o",
        tinyfish_api_key="tf-test",
        workspace_dir=tmp_path,
        bash_timeout=30,
        temperature=0.0,
        loaded_env_files=[str(tmp_path / ".env")],
    )

    banner = create_banner(cfg, session_title="Custom Session Title")
    assert banner is not None

    from xbot.sessions import SessionSummary
    dummy_sessions = [
        SessionSummary(
            id="sess_123",
            title="Build React App",
            created_at="2026-10-13T00:00:00",
            updated_at="2026-10-13T01:00:00",
            model_id="gpt-4o",
        )
    ]
    from xbot.tui.components import create_session_list_panel
    sess_panel = create_session_list_panel(dummy_sessions)
    assert sess_panel is not None

    help_panel = create_help_table()
    assert help_panel is not None

    config_panel = create_config_table(cfg)
    assert config_panel is not None

    tools_panel = create_tools_table()
    assert tools_panel is not None

    call_panel = create_tool_call_panel("bash", {"command": "ls -la"})
    assert call_panel is not None

    result_panel = create_tool_result_panel("bash", "Exit code: 0\nfile.txt", is_error=False)
    assert result_panel is not None

    error_panel = create_tool_result_panel("bash", "Exit code: 1", is_error=True)
    assert error_panel is not None


def test_tui_formatting():
    """Test markdown, json and truncation formatting."""
    md = format_markdown("# Hello\n```python\nprint(1)\n```")
    assert md is not None

    js = format_json({"key": "value", "list": [1, 2, 3]})
    assert js is not None

    short_text = "short"
    assert truncate_preview(short_text, max_chars=10) == "short"

    long_text = "a" * 50
    truncated = truncate_preview(long_text, max_chars=20)
    assert "truncated 30 characters" in truncated


import asyncio
from unittest.mock import MagicMock, patch
from xbot.tui.app import XBotTUI, listen_for_escape, poll_stdin_escape
from xbot.agent import AgentTextDelta


def test_poll_stdin_escape():
    """Test poll_stdin_escape correctly identifies standalone escape byte."""
    with patch("select.select", return_value=([1], [], [])):
        with patch("os.read", return_value=b"\x1b"):
            # Second select check for subsequent bytes returns empty (standalone Esc)
            with patch("select.select", side_effect=[([1], [], []), ([], [], [])]):
                assert poll_stdin_escape(0) is True

    # When a non-escape byte arrives
    with patch("select.select", return_value=([1], [], [])):
        with patch("os.read", return_value=b"a"):
            assert poll_stdin_escape(0) is False


@pytest.mark.asyncio
async def test_listen_for_escape_non_tty():
    """Test listen_for_escape exits immediately and cleanly when stdin is not a tty."""
    cancel_event = asyncio.Event()
    with patch("sys.stdin.isatty", return_value=False):
        await listen_for_escape(cancel_event)
        assert not cancel_event.is_set()


@pytest.mark.asyncio
async def test_tui_run_turn_interrupted(tmp_path):
    """Test run_turn cancels streaming when cancel_event is triggered."""
    cfg = Config(
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model_id="gpt-4o",
        tinyfish_api_key="tf-test",
        workspace_dir=tmp_path,
        bash_timeout=30,
        temperature=0.0,
        loaded_env_files=[],
    )

    mock_agent = MagicMock()
    mock_agent.config = cfg
    mock_agent.messages = []
    mock_agent.current_session = None

    async def slow_stream(prompt):
        yield AgentTextDelta("Hello world")
        await asyncio.sleep(2.0)
        yield AgentTextDelta(" More text")

    mock_agent.stream_turn = slow_stream
    tui = XBotTUI(agent_manager=mock_agent)

    # Trigger cancel_event right after the turn starts
    original_run_turn = tui.run_turn

    async def cancel_soon():
        await asyncio.sleep(0.05)
        # Find cancel_event or simulate Esc
        # We can simulate cancel by intercepting the event

    # Patch listen_for_escape to immediately set cancel_event after brief sleep
    async def mock_listen(cancel_event):
        await asyncio.sleep(0.05)
        cancel_event.set()

    with patch("xbot.tui.app.listen_for_escape", side_effect=mock_listen):
        await tui.run_turn("test question")

    # Verify that an assistant message with interrupted note was appended
    assert len(mock_agent.messages) > 0
    last_msg = mock_agent.messages[-1]
    assert "[Interrupted by user]" in str(last_msg)

