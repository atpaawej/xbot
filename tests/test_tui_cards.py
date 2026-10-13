"""Unit tests for specialized TUI tool cards and thinking visualization."""

import time
import pytest
from rich.console import Console
from rich.panel import Panel

from xbot.tui.cards import (
    ThinkingDrawer,
    ToolCardState,
    ToolState,
    render_bash_card,
    render_default_card,
    render_diff_card,
    render_file_read_card,
    render_file_write_card,
    render_glob_card,
    render_grep_card,
    render_tool_card,
    render_web_fetch_card,
    render_web_search_card,
)
from xbot.tui.cards.base import clean_rel_path, format_status_badge, truncate_head, truncate_tail


def test_base_utilities():
    """Test truncation and path cleaning utilities."""
    text = "line1\nline2\nline3\nline4\nline5"
    tail_text, omitted_tail = truncate_tail(text, max_lines=3)
    assert omitted_tail == 2
    assert tail_text == "line3\nline4\nline5"

    head_text, omitted_head = truncate_head(text, max_lines=2)
    assert omitted_head == 3
    assert head_text == "line1\nline2"

    short = "one\ntwo"
    res_tail, om_tail = truncate_tail(short, max_lines=5)
    assert om_tail == 0
    assert res_tail == short

    badge_run = format_status_badge(ToolState.RUNNING)
    assert "RUNNING" in badge_run.plain

    badge_done = format_status_badge(ToolState.SUCCESS)
    assert "DONE" in badge_done.plain

    badge_err = format_status_badge(ToolState.ERROR, is_error=True)
    assert "FAILED" in badge_err.plain


def test_bash_card_running_and_completed():
    """Test bash card rendering in RUNNING, SUCCESS, and ERROR states."""
    # 1. Running state
    state_run = ToolCardState(
        tool_name="bash",
        tool_call_id="call_1",
        args={"command": "pytest -v"},
        state=ToolState.RUNNING,
    )
    panel_run = render_bash_card(state_run)
    console = Console(record=True, width=120)
    console.print(panel_run)
    rendered_text = console.export_text()
    assert "pytest -v" in rendered_text

    # 2. Success state with exit code 0
    state_done = ToolCardState(
        tool_name="bash",
        tool_call_id="call_1",
        args={"command": "pytest -v"},
        state=ToolState.SUCCESS,
        result="Exit code: 0\nSTDOUT:\n55 passed in 2.0s",
        start_time=time.time() - 2.5,
        end_time=time.time(),
    )
    panel_done = render_bash_card(state_done)
    assert isinstance(panel_done, Panel)
    assert panel_done.border_style == "green"

    # 3. Error state with exit code 1
    state_err = ToolCardState(
        tool_name="bash",
        tool_call_id="call_1",
        args={"command": "pytest -v"},
        state=ToolState.ERROR,
        result="Exit code: 1\nSTDERR:\nAssertionError",
        is_error=True,
    )
    panel_err = render_bash_card(state_err)
    assert panel_err.border_style == "bold red"


def test_diff_card_rendering():
    """Test unified diff calculation and syntax diff card."""
    state = ToolCardState(
        tool_name="edit",
        tool_call_id="call_2",
        args={
            "path": "src/xbot/main.py",
            "target_content": "def old_foo():\n    return 1",
            "replacement_content": "def new_foo():\n    return 2\n    # extra line",
        },
        state=ToolState.SUCCESS,
        result="Successfully replaced 1 occurrence(s).",
    )
    panel = render_diff_card(state)
    assert isinstance(panel, Panel)
    assert panel.border_style == "green"

    # Error case
    state_err = ToolCardState(
        tool_name="edit",
        tool_call_id="call_2",
        args={"path": "src/xbot/main.py", "target_content": "xyz", "replacement_content": "abc"},
        state=ToolState.ERROR,
        result="Error: target_content not found in 'src/xbot/main.py'.",
        is_error=True,
    )
    panel_err = render_diff_card(state_err)
    assert panel_err.border_style == "bold red"


def test_file_read_anti_clutter():
    """Test read card does not dump entire file into scrollback."""
    full_content = "\n".join(f"line {i}" for i in range(100))
    state = ToolCardState(
        tool_name="read",
        tool_call_id="call_3",
        args={"path": "src/xbot/agent/core.py", "start_line": 1, "end_line": 100},
        state=ToolState.SUCCESS,
        result=full_content,
    )
    panel = render_file_read_card(state)
    assert isinstance(panel, Panel)
    console = Console(record=True, width=120)
    console.print(panel)
    rendered_text = console.export_text()
    assert "Content loaded into agent context" in rendered_text
    assert "line 99" not in rendered_text


def test_file_write_card():
    """Test file write card renders line count, byte size, and preview."""
    content = "import os\nimport sys\nprint('hello')\n"
    state = ToolCardState(
        tool_name="write",
        tool_call_id="call_4",
        args={"path": "test.py", "content": content},
        state=ToolState.SUCCESS,
        result="Successfully wrote 3 lines to 'test.py'.",
    )
    panel = render_file_write_card(state)
    assert isinstance(panel, Panel)
    assert panel.border_style == "green"


def test_grep_and_glob_cards():
    """Test grep and glob card renderers."""
    grep_state = ToolCardState(
        tool_name="grep",
        tool_call_id="call_5",
        args={"pattern": "class Agent", "path": "src/"},
        state=ToolState.SUCCESS,
        result="src/xbot/agent/core.py:66:class AgentManager:\nsrc/xbot/main.py:10:class App:",
    )
    grep_panel = render_grep_card(grep_state)
    assert isinstance(grep_panel, Panel)

    glob_state = ToolCardState(
        tool_name="glob",
        tool_call_id="call_6",
        args={"pattern": "*.py", "path": "src/"},
        state=ToolState.SUCCESS,
        result="src/xbot/main.py\nsrc/xbot/config.py",
    )
    glob_panel = render_glob_card(glob_state)
    assert isinstance(glob_panel, Panel)


def test_web_cards():
    """Test TinyFish web search and fetch cards."""
    search_state = ToolCardState(
        tool_name="web_search",
        tool_call_id="call_7",
        args={"query": "TinyFish SDK python", "purpose": "check docs"},
        state=ToolState.SUCCESS,
        result="Total results: 3\n1. TinyFish SDK: https://tinyfish.ai/docs\n2. GitHub: https://github.com/tinyfish",
    )
    search_panel = render_web_search_card(search_state)
    assert isinstance(search_panel, Panel)

    fetch_state = ToolCardState(
        tool_name="web_fetch",
        tool_call_id="call_8",
        args={"url": "https://tinyfish.ai/docs", "goal": "read api specs"},
        state=ToolState.SUCCESS,
        result="# TinyFish Documentation\nClean extracted markdown content...",
    )
    fetch_panel = render_web_fetch_card(fetch_state)
    assert isinstance(fetch_panel, Panel)


def test_polymorphic_dispatcher():
    """Test render_tool_card correctly routes to each tool."""
    tools = ["bash", "edit", "read", "write", "grep", "glob", "web_search", "web_fetch", "unknown_custom"]
    for t in tools:
        state = ToolCardState(tool_name=t, tool_call_id="test", state=ToolState.RUNNING)
        panel = render_tool_card(state)
        assert isinstance(panel, Panel)


def test_thinking_drawer():
    """Test ThinkingDrawer live preview and collapsed summary."""
    drawer = ThinkingDrawer()
    drawer.append("First thought line.\n")
    drawer.append("Second thought line analyzing the codebase.\n")

    live_panel = drawer.render_live()
    assert isinstance(live_panel, Panel)
    assert "Thinking..." in str(live_panel.title)

    drawer.finalize()
    assert drawer.end_time is not None

    collapsed_pill = drawer.render_collapsed()
    assert "Thought for" in collapsed_pill.plain
    assert "Second thought line analyzing the codebase" in collapsed_pill.plain
