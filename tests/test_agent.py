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


def test_system_prompt_behavioral_directives(tmp_path):
    """Test system prompt includes Top 1% behavioral directives and operational phases."""
    prompt = get_system_prompt(tmp_path)
    # Check behavioral principles
    assert "Operating Principles & Mindset" in prompt
    assert "Autonomous Bias" in prompt
    assert "Zero Fluff & Anti-Sycophancy" in prompt
    assert "The 4-Stage Operational Lifecycle" in prompt
    assert "DISCOVER & ORIENT" in prompt
    assert "SURGICAL EXECUTION" in prompt
    assert "EMPIRICAL VERIFICATION" in prompt
    assert "Two-Strike Rule" in prompt
    assert "Error Recovery & Anti-Looping Protocol" in prompt
    assert "Environment Context" in prompt
    assert "Operating System:" in prompt


def test_system_prompt_loads_agents_md(tmp_path):
    """Test auto-loading of AGENTS.md into system prompt."""
    agents_file = tmp_path / "AGENTS.md"
    agents_file.write_text("# Project Custom Rules\nAlways run ruff check before commits.")

    prompt = get_system_prompt(tmp_path)
    assert "Project-Specific Instructions & Guidelines (AGENTS.md / CLAUDE.md)" in prompt
    assert "AGENTS.md" in prompt
    assert "Always run ruff check before commits." in prompt


def test_system_prompt_loads_claude_md(tmp_path):
    """Test auto-loading of CLAUDE.md into system prompt."""
    claude_file = tmp_path / "CLAUDE.md"
    claude_file.write_text("# Claude Architecture Guidelines\nUse async/await for network calls.")

    prompt = get_system_prompt(tmp_path)
    assert "Project-Specific Instructions & Guidelines (AGENTS.md / CLAUDE.md)" in prompt
    assert "CLAUDE.md" in prompt
    assert "Use async/await for network calls." in prompt


def test_system_prompt_loads_both_and_truncates(tmp_path):
    """Test loading both AGENTS.md and CLAUDE.md, and respect truncation guardrails."""
    agents_file = tmp_path / "AGENTS.md"
    agents_file.write_text("Instruction A " * 100)

    claude_file = tmp_path / "CLAUDE.md"
    claude_file.write_text("Instruction B " * 100)

    from xbot.agent import load_project_instructions

    # Test combined load
    combined = load_project_instructions(tmp_path, max_chars=10000)
    assert "AGENTS.md" in combined
    assert "CLAUDE.md" in combined
    assert "Instruction A" in combined
    assert "Instruction B" in combined

    # Test truncation guardrail
    truncated = load_project_instructions(tmp_path, max_chars=50)
    assert "truncated" in truncated or "omitted" in truncated


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
