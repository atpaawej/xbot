"""Tests for AgentManager and agent core module."""

import pytest
from xbot.agent import (
    AgentError,
    AgentManager,
    AgentReasoningDelta,
    AgentTextDelta,
    AgentToolEnd,
    AgentToolResult,
    AgentToolStart,
    get_system_prompt,
)
from xbot.config import Config


def test_system_prompt_generation(tmp_path):
    """Test system prompt includes workspace directory and core tools."""
    prompt = get_system_prompt(tmp_path)
    assert str(tmp_path.resolve()) in prompt
    assert "bash" in prompt
    assert "write" in prompt
    assert "edit" in prompt
    assert "read" in prompt
    assert "grep" in prompt
    assert "glob" in prompt
    assert "web_search" in prompt
    assert "web_fetch" in prompt
    assert "TinyFish" in prompt


def test_agent_manager_initialization(tmp_path):
    """Test AgentManager sets up tools, model, and message history."""
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
    manager = AgentManager(config=cfg)
    assert manager.model.id == "gpt-4o"
    assert len(manager.agent.tools) == 8
    assert len(manager.messages) == 1  # System message


@pytest.mark.asyncio
async def test_agent_unconfigured_error(tmp_path):
    """Test that stream_turn yields AgentError when API key is missing."""
    cfg = Config(
        base_url="https://api.openai.com/v1",
        api_key="",
        model_id="gpt-4o",
        tinyfish_api_key="",
        workspace_dir=tmp_path,
        bash_timeout=30,
        temperature=0.0,
        loaded_env_files=[],
    )
    manager = AgentManager(config=cfg)

    events = []
    async for ev in manager.stream_turn("Hello"):
        events.append(ev)

    assert len(events) == 1
    assert isinstance(events[0], AgentError)
    assert "LLM Provider API key is not configured" in events[0].error_message
