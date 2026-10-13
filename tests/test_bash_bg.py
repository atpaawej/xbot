"""Tests for upgraded bash tool with background tasks."""

import asyncio
import pytest
from xbot.config import Config, set_config
from xbot.tools import bash


@pytest.fixture(autouse=True)
def setup_workspace(tmp_path):
    cfg = Config(
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model_id="gpt-4o",
        tinyfish_api_key="",
        workspace_dir=tmp_path,
        bash_timeout=5,
        temperature=0.0,
        loaded_env_files=[],
    )
    set_config(cfg)
    yield tmp_path


@pytest.mark.asyncio
async def test_bash_sync_run():
    """Test standard synchronous command execution."""
    res = await bash.fn("echo 'hello sync'")
    assert "Exit code: 0" in res
    assert "hello sync" in res


@pytest.mark.asyncio
async def test_bash_background_workflow():
    """Test launching, checking status, listing, and killing a background task."""
    # Launch background task
    start_res = await bash.fn("sleep 5", is_bg=True)
    assert "Started background task" in start_res

    # Extract task ID
    import re
    match = re.search(r"'(bg_\d+)'", start_res)
    assert match is not None
    task_id = match.group(1)

    # List tasks
    list_res = await bash.fn(action="list")
    assert task_id in list_res
    assert "Status: running" in list_res

    # Check status
    status_res = await bash.fn(action="status", task_id=task_id)
    assert f"Task ID: {task_id}" in status_res
    assert "Status: running" in status_res

    # Terminate / kill task
    kill_res = await bash.fn(action="kill", task_id=task_id)
    assert "Successfully sent termination signal" in kill_res

    # Verify status reflects termination
    post_kill = await bash.fn(action="status", task_id=task_id)
    assert "Status: killed" in post_kill
