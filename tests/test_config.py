"""Tests for configuration module."""

import os
import tempfile
from pathlib import Path

from xbot.config import Config, get_config, load_env_files


def test_config_defaults(tmp_path, monkeypatch):
    """Test default values when no environment variables are set."""
    for key in ["OPENAI_BASE_URL", "BASE_URL", "OPENAI_API_KEY", "API_KEY", "MODEL_ID", "MODEL_NAME", "TINYFISH_API_KEY"]:
        monkeypatch.delenv(key, raising=False)

    config = Config.load(base_path=tmp_path)
    assert config.base_url == "https://api.openai.com/v1"
    assert config.model_id == "gpt-4o"
    assert config.api_key == ""
    assert config.tinyfish_api_key == ""
    assert not config.is_llm_configured
    assert not config.is_tinyfish_configured


def test_env_local_precedence(tmp_path):
    """Test that .env.local overrides values from .env."""
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=base_key\nMODEL_ID=gpt-3.5-turbo\n", encoding="utf-8")

    env_local_file = tmp_path / ".env.local"
    env_local_file.write_text("OPENAI_API_KEY=override_key\nMODEL_ID=gpt-4o\n", encoding="utf-8")

    loaded = load_env_files(tmp_path)
    assert len(loaded) == 2

    config = Config.load(tmp_path)
    assert config.api_key == "override_key"
    assert config.model_id == "gpt-4o"
    assert config.is_llm_configured


def test_masking_secrets():
    """Test API key masking logic."""
    config = Config(
        base_url="https://api.openai.com/v1",
        api_key="sk-1234567890abcdef",
        model_id="gpt-4o",
        tinyfish_api_key="tf-sec-abcdef123456",
        workspace_dir=Path("/tmp"),
        bash_timeout=60,
        temperature=0.0,
        loaded_env_files=[],
    )

    assert config.masked_api_key == "sk-1...cdef"
    assert config.masked_tinyfish_key == "tf-s...3456"
