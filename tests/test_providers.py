"""Tests for multi-provider architecture, canonical model parsing, auth storage, and provider commands."""

import os
import stat
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.console import Console

from xbot.commands.base import CommandContext
from xbot.commands.builtin.login import LoginCommand
from xbot.commands.builtin.model import ModelCommand
from xbot.providers import (
    AuthStore,
    LiteLLMProtocol,
    LiteLLMProvider,
    ModelInfo,
    ProviderManager,
    ProviderProfile,
    ProviderRegistry,
    canonical_model_id,
    enrich_model_metadata,
    fetch_provider_models,
    get_auth_store,
    get_provider_manager,
    get_provider_registry,
    parse_model_ref,
)


class TestCanonicalModelParsing:
    """Test strict 'provider/model_id' parsing and formatting rules."""

    def test_parse_valid_canonical_models(self):
        p, m = parse_model_ref("anthropic/claude-3-7-sonnet-20250219")
        assert p == "anthropic"
        assert m == "claude-3-7-sonnet-20250219"

        p, m = parse_model_ref("openai/gpt-4o")
        assert p == "openai"
        assert m == "gpt-4o"

        p, m = parse_model_ref("deepseek/deepseek-reasoner")
        assert p == "deepseek"
        assert m == "deepseek-reasoner"

        p, m = parse_model_ref("groq/llama-3.3-70b-versatile")
        assert p == "groq"
        assert m == "llama-3.3-70b-versatile"

    def test_parse_rejects_bare_model_id(self):
        with pytest.raises(ValueError, match="Models must be specified as 'provider/model_id'"):
            parse_model_ref("gpt-4o")

        with pytest.raises(ValueError, match="Models must be specified as 'provider/model_id'"):
            parse_model_ref("claude-3-7-sonnet")

        with pytest.raises(ValueError, match="Models must be specified as 'provider/model_id'"):
            parse_model_ref("llama3.2")

    def test_parse_rejects_empty_or_whitespace(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            parse_model_ref("")
        with pytest.raises(ValueError, match="cannot be empty"):
            parse_model_ref("   ")

    def test_parse_rejects_missing_parts(self):
        with pytest.raises(ValueError, match="Both provider and model_id must be non-empty"):
            parse_model_ref("/gpt-4o")
        with pytest.raises(ValueError, match="Both provider and model_id must be non-empty"):
            parse_model_ref("openai/")

    def test_canonical_model_id_formatter(self):
        assert canonical_model_id("anthropic", "claude-3-7-sonnet") == "anthropic/claude-3-7-sonnet"
        assert canonical_model_id("OPENAI", "gpt-4o") == "openai/gpt-4o"
        # Does not duplicate if already prefixed
        assert canonical_model_id("openai", "openai/gpt-4o") == "openai/gpt-4o"


class TestProviderRegistry:
    """Test registry configurations and alias resolution."""

    def test_prebuilt_providers_exist(self):
        reg = get_provider_registry()
        expected_ids = [
            "openai",
            "anthropic",
            "gemini",
            "groq",
            "xai",
            "deepseek",
            "moonshot",
            "alibaba",
            "minimax",
            "zhipu",
            "siliconflow",
            "ollama",
            "openrouter",
        ]
        for p_id in expected_ids:
            profile = reg.get(p_id)
            assert profile is not None, f"Expected provider '{p_id}' in registry"
            assert "/" in profile.default_model, f"Default model '{profile.default_model}' must be canonical"

    def test_provider_alias_resolution(self):
        reg = get_provider_registry()
        assert reg.get("claude").id == "anthropic"
        assert reg.get("google").id == "gemini"
        assert reg.get("grok").id == "xai"
        assert reg.get("kimi").id == "moonshot"
        assert reg.get("qwen").id == "alibaba"
        assert reg.get("local").id == "ollama"

    def test_custom_provider_registration(self):
        reg = ProviderRegistry()
        custom = ProviderProfile(
            id="vllm-local",
            name="Local vLLM",
            category="Local",
            default_base_url="http://localhost:8000/v1",
            default_model="vllm-local/mistral-7b",
        )
        reg.register(custom)
        assert reg.get("vllm-local") == custom


class TestAuthStore:
    """Test multi-provider auth persistence, atomic file write, and 0600 permissions."""

    def test_multi_provider_storage_and_permissions(self, tmp_path: Path):
        auth_file = tmp_path / "sub" / "auth.json"
        store = AuthStore(auth_file)

        # 1. Save provider 1 (OpenAI)
        store.save_provider_auth(
            provider_id="openai",
            api_key="sk-test-openai",
            default_model="openai/gpt-4o",
            set_as_active=True,
        )

        assert auth_file.is_file()
        # Verify file permissions 0600
        mode = oct(stat.S_IMODE(os.stat(auth_file).st_mode))
        assert mode == "0o600"

        # 2. Save provider 2 (Anthropic) - must coexist!
        store.save_provider_auth(
            provider_id="anthropic",
            api_key="sk-test-anthropic",
            default_model="anthropic/claude-3-7-sonnet-20250219",
            set_as_active=True,
        )

        data = store.load()
        assert "openai" in data.providers
        assert "anthropic" in data.providers
        assert data.providers["openai"].api_key == "sk-test-openai"
        assert data.providers["anthropic"].api_key == "sk-test-anthropic"
        assert data.active_model == "anthropic/claude-3-7-sonnet-20250219"

        # 3. Resolve credentials
        key, base_url = store.resolve_credentials("openai")
        assert key == "sk-test-openai"
        assert base_url == "https://api.openai.com/v1"

        key, base_url = store.resolve_credentials("anthropic")
        assert key == "sk-test-anthropic"
        assert base_url == "https://api.anthropic.com/v1"

    def test_remove_provider(self, tmp_path: Path):
        auth_file = tmp_path / "auth.json"
        store = AuthStore(auth_file)
        store.save_provider_auth("groq", "gsk-test", "groq/llama-3.3-70b", set_as_active=True)

        assert store.remove_provider_auth("groq") is True
        assert "groq" not in store.load().providers
        assert store.load().active_model is None
        assert store.remove_provider_auth("groq") is False


class TestProviderManager:
    """Test ProviderManager runtime model instantiation and switching."""

    def test_provider_manager_switch_and_instantiate(self, tmp_path: Path):
        auth_file = tmp_path / "auth.json"
        store = AuthStore(auth_file)
        store.save_provider_auth("anthropic", "sk-ant-test", "anthropic/claude-3-7-sonnet-20250219")

        pm = ProviderManager(auth_store=store)
        assert pm.active_model == "anthropic/claude-3-7-sonnet-20250219"
        assert pm.active_provider_id == "anthropic"

        # Switch to DeepSeek
        switched = pm.switch_model("deepseek/deepseek-reasoner")
        assert switched == "deepseek/deepseek-reasoner"
        assert pm.active_model == "deepseek/deepseek-reasoner"
        assert pm.active_provider_id == "deepseek"

        # Model instantiation
        model = pm.create_model()
        assert model.id == "deepseek/deepseek-reasoner"
        assert isinstance(model.provider, LiteLLMProvider)
        assert isinstance(model.protocol, LiteLLMProtocol)

    def test_switch_rejects_bare_model(self, tmp_path: Path):
        pm = ProviderManager(auth_store=AuthStore(tmp_path / "auth.json"))
        with pytest.raises(ValueError, match="Models must be specified as 'provider/model_id'"):
            pm.switch_model("gpt-4o")


@pytest.mark.asyncio
class TestModelFetcher:
    """Test dynamic live model fetching and enrichment."""

    async def test_fetcher_with_mock_endpoint(self, tmp_path: Path):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "llama-3.3-70b-versatile"},
                {"id": "mixtral-8x7b-32768"},
            ]
        }

        with patch("os.getenv", return_value=str(tmp_path)):
            with patch("httpx.AsyncClient.get", return_value=mock_response):
                models = await fetch_provider_models(
                    provider_id="groq",
                    api_key="test-key",
                    force_refresh=True,
                )

        assert len(models) >= 2
        for m in models:
            assert m.full_id.startswith("groq/")
            assert m.provider_id == "groq"

        # Check metadata enrichment
        meta = enrich_model_metadata("deepseek", "deepseek-reasoner")
        assert meta["supports_reasoning"] is True


@pytest.mark.asyncio
class TestProviderCommands:
    """Test /model and /login command handling."""

    async def test_model_command_direct_switch_canonical(self, tmp_path: Path):
        auth_file = tmp_path / "auth.json"
        store = AuthStore(auth_file)
        store.save_provider_auth("anthropic", "sk-test", "anthropic/claude-3-7-sonnet-20250219")

        console = Console(record=True)
        agent_manager = MagicMock()

        cmd = ModelCommand()
        context = CommandContext(
            console=console,
            agent_manager=agent_manager,
            raw_args="deepseek/deepseek-reasoner",
        )

        with patch("xbot.commands.builtin.model.get_auth_store", return_value=store):
            res = await cmd.execute(context)

        assert res.handled is True
        agent_manager.switch_model.assert_called_with("deepseek/deepseek-reasoner")
        output = console.export_text()
        assert "Active model successfully switched" in output

    async def test_model_command_rejects_bare_model(self):
        console = Console(record=True)
        agent_manager = MagicMock()

        cmd = ModelCommand()
        context = CommandContext(
            console=console,
            agent_manager=agent_manager,
            raw_args="gpt-4o",  # Bare model!
        )

        res = await cmd.execute(context)
        assert res.handled is True
        output = console.export_text()
        assert "Invalid Model Format" in output
        assert "provider/model_id" in output
        agent_manager.switch_model.assert_not_called()
