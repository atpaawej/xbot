"""Unit tests for xbot core tools."""

import asyncio
import os
from pathlib import Path

import pytest
from xbot.config import Config, get_config
from xbot.tools import (
    ALL_TOOLS,
    bash,
    edit,
    glob,
    grep,
    read,
    web_fetch,
    web_search,
    write,
)


@pytest.fixture(autouse=True)
def setup_workspace(tmp_path, monkeypatch):
    """Set workspace directory to a clean temp directory for each test."""
    monkeypatch.setenv("WORKSPACE_DIR", str(tmp_path))
    monkeypatch.delenv("TINYFISH_API_KEY", raising=False)
    from xbot.config import set_config
    cfg = Config(
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model_id="gpt-4o",
        tinyfish_api_key="",
        workspace_dir=tmp_path,
        bash_timeout=30,
        temperature=0.0,
        loaded_env_files=[],
    )
    set_config(cfg)
    yield tmp_path


@pytest.mark.asyncio
async def test_all_tools_count():
    """Verify all 8 core tools are registered."""
    assert len(ALL_TOOLS) == 8
    tool_names = [t.tool.name for t in ALL_TOOLS]
    expected = [
        "bash",
        "write",
        "edit",
        "read",
        "grep",
        "glob",
        "web_search",
        "web_fetch",
    ]
    for exp in expected:
        assert exp in tool_names


@pytest.mark.asyncio
async def test_bash_execution():
    """Test bash command execution and return codes."""
    res = await bash.fn("echo 'test-output'")
    assert "Exit code: 0" in res
    assert "test-output" in res

    fail_res = await bash.fn("exit 42")
    assert "Exit code: 42" in fail_res


@pytest.mark.asyncio
async def test_write_and_read(setup_workspace):
    """Test file writing and line-numbered reading."""
    write_res = await write.fn("sample.txt", "Line 1\nLine 2\nLine 3\n")
    assert "Successfully wrote" in write_res

    target_file = setup_workspace / "sample.txt"
    assert target_file.exists()
    assert target_file.read_text(encoding="utf-8") == "Line 1\nLine 2\nLine 3\n"

    read_res = await read.fn("sample.txt")
    assert "--- sample.txt (lines 1-3 of 3) ---" in read_res
    assert "     1 | Line 1" in read_res
    assert "     2 | Line 2" in read_res
    assert "     3 | Line 3" in read_res

    # Slice range test
    slice_res = await read.fn("sample.txt", start_line=2, end_line=2)
    assert "lines 2-2 of 3" in slice_res
    assert "     2 | Line 2" in slice_res
    assert "     1 | Line 1" not in slice_res


@pytest.mark.asyncio
async def test_read_directory_listing(setup_workspace):
    """Test read tool listing directory contents (action='list' or auto-directory)."""
    (setup_workspace / "subdir").mkdir(parents=True, exist_ok=True)
    (setup_workspace / "file_a.py").write_text("a = 1")
    (setup_workspace / "file_b.txt").write_text("hello")

    # Explicit action='list'
    list_res = await read.fn(".", action="list")
    assert "Directory listing" in list_res
    assert "[DIR]  subdir/" in list_res
    assert "[FILE] file_a.py" in list_res
    assert "[FILE] file_b.txt" in list_res

    # Auto-detection when passing directory path
    auto_res = await read.fn(".")
    assert "Directory listing" in auto_res
    assert "[DIR]  subdir/" in auto_res


@pytest.mark.asyncio
async def test_edit(setup_workspace):
    """Test editing files with exact replacement."""
    await write.fn("code.py", "def hello():\n    print('world')\n")

    # Non-existent target error
    err_res = await edit.fn("code.py", "missing text", "replacement")
    assert "Error: target_content not found" in err_res

    # Successful replacement
    success_res = await edit.fn(
        "code.py", "print('world')", "print('xbot')"
    )
    assert "Successfully replaced 1 occurrence(s)" in success_res

    content = (setup_workspace / "code.py").read_text(encoding="utf-8")
    assert "print('xbot')" in content
    assert "print('world')" not in content


@pytest.mark.asyncio
async def test_edit_multiple_matches_safeguard(setup_workspace):
    """Test that multiple matches are rejected without allow_multiple flag."""
    await write.fn("dup.txt", "foo\nbar\nfoo\n")
    dup_res = await edit.fn("dup.txt", "foo", "baz", allow_multiple=False)
    assert "found 2 times" in dup_res

    # Should succeed with allow_multiple=True
    allowed_res = await edit.fn("dup.txt", "foo", "baz", allow_multiple=True)
    assert "Successfully replaced 2 occurrence(s)" in allowed_res


@pytest.mark.asyncio
async def test_grep_and_glob(setup_workspace):
    """Test pattern searching and glob matching."""
    await write.fn("src/app.py", "def main():\n    pass\n")
    await write.fn("src/utils.py", "# Helper function\ndef helper():\n    pass\n")

    glob_res = await glob.fn("src/*.py")
    assert "Matched 2 item(s)" in glob_res
    assert "src/app.py" in glob_res
    assert "src/utils.py" in glob_res

    grep_res = await grep.fn("def helper")
    assert "Found 1 match(es)" in grep_res
    assert "src/utils.py:2: def helper():" in grep_res


@pytest.mark.asyncio
async def test_web_search_without_key():
    """Test that web_search returns helpful instruction when TinyFish key is unconfigured."""
    res = await web_search.fn("python async tutorial")
    assert "TinyFish API key is not configured" in res
    assert "https://agent.tinyfish.ai/api-keys" in res


@pytest.mark.asyncio
async def test_web_fetch_without_key():
    """Test that web_fetch returns helpful instruction when TinyFish key is unconfigured."""
    res = await web_fetch.fn("https://example.com")
    assert "TinyFish API key is not configured" in res
    assert "https://agent.tinyfish.ai/api-keys" in res
