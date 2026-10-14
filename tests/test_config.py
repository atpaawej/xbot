"""Tests for configuration module."""

import json
import os
from pathlib import Path

from xbot.config import (
    Config,
    get_config,
    get_config_file_paths,
    load_env_files,
    strip_json_comments,
    update_setting,
)


def test_config_defaults(tmp_path, monkeypatch):
    """Test default values when no environment variables or settings files are set."""
    for key in [
        "OPENAI_BASE_URL",
        "BASE_URL",
        "OPENAI_API_KEY",
        "API_KEY",
        "MODEL_ID",
        "MODEL_NAME",
        "TINYFISH_API_KEY",
        "XBOT_DATA_DIR",
    ]:
        monkeypatch.delenv(key, raising=False)

    data_dir = tmp_path / "global_xbot"
    config = Config.load(base_path=tmp_path, data_dir=data_dir)
    assert config.base_url == "https://api.openai.com/v1"
    assert config.model_id == "gpt-4o"
    assert config.api_key == ""
    assert config.tinyfish_api_key == ""
    assert not config.is_llm_configured
    assert not config.is_tinyfish_configured


def test_strip_json_comments():
    """Test stripping single-line, multi-line comments, and trailing commas from JSON string."""
    raw = """
    {
        // This is a single line comment
        "model": "claude-3-5-sonnet", /* inline comment */
        "base_url": "https://api.anthropic.com // not a comment",
        /*
          Multi-line
          block comment
        */
        "temperature": 0.5,
    }
    """
    clean = strip_json_comments(raw)
    assert "// This is a single line comment" not in clean
    assert "/* inline comment */" not in clean
    assert "Multi-line" not in clean
    assert "https://api.anthropic.com // not a comment" in clean


def test_global_settings_json(tmp_path, monkeypatch):
    """Test loading configuration from global settings.json."""
    for key in [
        "OPENAI_BASE_URL",
        "BASE_URL",
        "OPENAI_API_KEY",
        "API_KEY",
        "MODEL_ID",
        "MODEL_NAME",
        "TINYFISH_API_KEY",
    ]:
        monkeypatch.delenv(key, raising=False)

    data_dir = tmp_path / "global_xbot"
    data_dir.mkdir(parents=True)
    settings_file = data_dir / "settings.json"
    settings_file.write_text(
        json.dumps({
            "model_id": "claude-3-7-sonnet",
            "api_key": "sk-global-key",
            "base_url": "https://api.anthropic.com",
            "bash_timeout": 60,
        }),
        encoding="utf-8",
    )

    config = Config.load(base_path=tmp_path, data_dir=data_dir)
    assert config.model_id == "claude-3-7-sonnet"
    assert config.api_key == "sk-global-key"
    assert config.base_url == "https://api.anthropic.com"
    assert config.bash_timeout == 60
    assert str(settings_file) in config.loaded_config_files


def test_project_settings_overrides_global(tmp_path, monkeypatch):
    """Test that project .xbot/settings.json overrides global settings.json."""
    for key in [
        "OPENAI_BASE_URL",
        "BASE_URL",
        "OPENAI_API_KEY",
        "API_KEY",
        "MODEL_ID",
        "MODEL_NAME",
        "TINYFISH_API_KEY",
    ]:
        monkeypatch.delenv(key, raising=False)

    data_dir = tmp_path / "global_xbot"
    data_dir.mkdir(parents=True)
    (data_dir / "settings.json").write_text(
        json.dumps({
            "model_id": "global-model",
            "api_key": "global-api-key",
            "bash_timeout": 60,
        }),
        encoding="utf-8",
    )

    project_dir = tmp_path / "my_project"
    project_xbot = project_dir / ".xbot"
    project_xbot.mkdir(parents=True)
    (project_xbot / "settings.json").write_text(
        json.dumps({
            "model_id": "project-model",
            "bash_timeout": 180,
        }),
        encoding="utf-8",
    )

    config = Config.load(base_path=project_dir, data_dir=data_dir)
    # Project overrides
    assert config.model_id == "project-model"
    assert config.bash_timeout == 180
    # Global fallback for keys not in project settings
    assert config.api_key == "global-api-key"
    assert len(config.loaded_config_files) == 2


def test_settings_json_overrides_env_local(tmp_path, monkeypatch):
    """Test that settings.json takes precedence over .env.local, but falls back for missing keys."""
    for key in ["OPENAI_API_KEY", "API_KEY", "MODEL_ID", "MODEL_NAME"]:
        monkeypatch.delenv(key, raising=False)

    data_dir = tmp_path / "global_xbot"
    data_dir.mkdir(parents=True)
    (data_dir / "settings.json").write_text(
        json.dumps({
            "model_id": "settings-model",
            # api_key omitted intentionally to test fallback
        }),
        encoding="utf-8",
    )

    # .env.local in project root
    (tmp_path / ".env.local").write_text(
        "MODEL_ID=env-local-model\nOPENAI_API_KEY=env-local-key\n",
        encoding="utf-8",
    )

    config = Config.load(base_path=tmp_path, data_dir=data_dir)
    # settings.json overrides .env.local
    assert config.model_id == "settings-model"
    # .env.local falls back for keys not in settings.json
    assert config.api_key == "env-local-key"

    # Explicit process environment / CLI flag overrides settings.json
    monkeypatch.setenv("MODEL_ID", "cli-override-model")
    config2 = Config.load(base_path=tmp_path, data_dir=data_dir)
    assert config2.model_id == "cli-override-model"


def test_update_setting_global_and_project(tmp_path, monkeypatch):
    """Test update_setting mutates files and reloads configuration properly."""
    for key in ["MODEL_ID", "MODEL_NAME", "OPENAI_API_KEY", "API_KEY"]:
        monkeypatch.delenv(key, raising=False)

    data_dir = tmp_path / "data"
    project_dir = tmp_path / "proj"
    project_dir.mkdir(parents=True)

    # 1. Update global setting
    cfg = update_setting(
        key="model",  # alias for model_id
        value="gpt-4.5-preview",
        scope="global",
        base_path=project_dir,
        data_dir=data_dir,
    )
    assert cfg.model_id == "gpt-4.5-preview"
    global_file = data_dir / "settings.json"
    assert global_file.is_file()
    data = json.loads(global_file.read_text())
    assert data["model_id"] == "gpt-4.5-preview"

    # 2. Update project setting
    cfg2 = update_setting(
        key="bash_timeout",
        value="300",
        scope="project",
        base_path=project_dir,
        data_dir=data_dir,
    )
    assert cfg2.bash_timeout == 300
    project_file = project_dir / ".xbot" / "settings.json"
    assert project_file.is_file()
    p_data = json.loads(project_file.read_text())
    assert p_data["bash_timeout"] == 300


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
