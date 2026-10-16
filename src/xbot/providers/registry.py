"""Provider registry holding prebuilt provider definitions and dynamic extensions."""

from __future__ import annotations

from typing import Optional
from xbot.providers.models import ProviderProfile


class ProviderRegistry:
    """Registry maintaining supported LLM provider configurations."""

    def __init__(self) -> None:
        self._providers: dict[str, ProviderProfile] = {}
        self._aliases: dict[str, str] = {
            "claude": "anthropic",
            "google": "gemini",
            "grok": "xai",
            "kimi": "moonshot",
            "qwen": "alibaba",
            "dashscope": "alibaba",
            "glm": "zhipu",
            "local": "ollama",
        }
        self._register_defaults()

    def register(self, profile: ProviderProfile) -> None:
        """Register or override a provider profile."""
        clean_id = profile.id.strip().lower()
        self._providers[clean_id] = profile

    def register_alias(self, alias: str, provider_id: str) -> None:
        """Register a friendly alias pointing to a provider_id."""
        self._aliases[alias.strip().lower()] = provider_id.strip().lower()

    def get(self, provider_id_or_alias: str) -> Optional[ProviderProfile]:
        """Look up provider profile by ID or alias."""
        clean = (provider_id_or_alias or "").strip().lower()
        resolved_id = self._aliases.get(clean, clean)
        return self._providers.get(resolved_id)

    def resolve_provider_id(self, provider_id_or_alias: str) -> str:
        """Resolve an alias to its canonical provider ID."""
        clean = (provider_id_or_alias or "").strip().lower()
        return self._aliases.get(clean, clean)

    def all_providers(self) -> list[ProviderProfile]:
        """Return all registered provider profiles in display order."""
        return list(self._providers.values())

    def providers_by_category(self) -> dict[str, list[ProviderProfile]]:
        """Return providers grouped by category."""
        grouped: dict[str, list[ProviderProfile]] = {}
        for p in self.all_providers():
            grouped.setdefault(p.category, []).append(p)
        return grouped

    def _register_defaults(self) -> None:
        """Register prebuilt first-class providers."""
        # Major US Providers
        self.register(
            ProviderProfile(
                id="openai",
                name="OpenAI",
                category="Major",
                protocol="openai",
                default_base_url="https://api.openai.com/v1",
                models_endpoint="/v1/models",
                auth_env_vars=["OPENAI_API_KEY"],
                default_model="openai/gpt-4o",
                flagship_models=[
                    "openai/gpt-4o",
                    "openai/gpt-4o-mini",
                    "openai/o1",
                    "openai/o3-mini",
                ],
                doc_url="https://platform.openai.com/docs",
                description="Industry standard GPT-4o, o1, and o3-mini models",
            )
        )
        self.register(
            ProviderProfile(
                id="anthropic",
                name="Anthropic (Claude)",
                category="Major",
                protocol="anthropic",
                default_base_url="https://api.anthropic.com/v1",
                models_endpoint="/v1/models",
                auth_env_vars=["ANTHROPIC_API_KEY"],
                default_model="anthropic/claude-3-7-sonnet-20250219",
                flagship_models=[
                    "anthropic/claude-3-7-sonnet-20250219",
                    "anthropic/claude-3-5-sonnet-20241022",
                    "anthropic/claude-3-5-haiku-20241022",
                ],
                doc_url="https://docs.anthropic.com",
                description="State-of-the-art Claude 3.7 Sonnet (Hybrid Reasoning)",
            )
        )
        self.register(
            ProviderProfile(
                id="gemini",
                name="Google Gemini",
                category="Major",
                protocol="openai",
                default_base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                models_endpoint="/models",
                auth_env_vars=["GEMINI_API_KEY", "GOOGLE_API_KEY"],
                default_model="gemini/gemini-2.5-flash",
                flagship_models=[
                    "gemini/gemini-2.5-flash",
                    "gemini/gemini-2.5-pro",
                    "gemini/gemini-2.0-flash",
                ],
                doc_url="https://ai.google.dev",
                description="Google Gemini 2.5 Flash & Pro with huge context windows",
            )
        )
        self.register(
            ProviderProfile(
                id="xai",
                name="xAI (Grok)",
                category="Major",
                protocol="openai",
                default_base_url="https://api.x.ai/v1",
                models_endpoint="/v1/models",
                auth_env_vars=["XAI_API_KEY"],
                default_model="xai/grok-2",
                flagship_models=["xai/grok-2", "xai/grok-2-vision-1212", "xai/grok-beta"],
                doc_url="https://docs.x.ai",
                description="Elon Musk's xAI Grok frontier models",
            )
        )

        # Fast Inference Providers
        self.register(
            ProviderProfile(
                id="groq",
                name="Groq LPU",
                category="Fast Inference",
                protocol="openai",
                default_base_url="https://api.groq.com/openai/v1",
                models_endpoint="/v1/models",
                auth_env_vars=["GROQ_API_KEY"],
                default_model="groq/llama-3.3-70b-versatile",
                flagship_models=[
                    "groq/llama-3.3-70b-versatile",
                    "groq/llama-3.1-8b-instant",
                    "groq/mixtral-8x7b-32768",
                ],
                doc_url="https://console.groq.com",
                description="Ultra low-latency LPU inference for open weights",
            )
        )
        self.register(
            ProviderProfile(
                id="deepseek",
                name="DeepSeek",
                category="Fast Inference",
                protocol="openai",
                default_base_url="https://api.deepseek.com",
                models_endpoint="/models",
                auth_env_vars=["DEEPSEEK_API_KEY"],
                default_model="deepseek/deepseek-reasoner",
                flagship_models=[
                    "deepseek/deepseek-reasoner",
                    "deepseek/deepseek-chat",
                ],
                doc_url="https://api-docs.deepseek.com",
                description="Breakthrough reasoning (R1) & general models (V3)",
            )
        )

        # Chinese Flagship Providers
        self.register(
            ProviderProfile(
                id="moonshot",
                name="Moonshot / Kimi",
                category="Chinese",
                protocol="openai",
                default_base_url="https://api.moonshot.cn/v1",
                models_endpoint="/v1/models",
                auth_env_vars=["MOONSHOT_API_KEY"],
                default_model="moonshot/moonshot-v1-8k",
                flagship_models=["moonshot/moonshot-v1-8k", "moonshot/moonshot-v1-32k", "moonshot/moonshot-v1-128k"],
                doc_url="https://platform.moonshot.cn",
                description="Moonshot AI (Kimi for Coding) long-context models",
            )
        )
        self.register(
            ProviderProfile(
                id="alibaba",
                name="Alibaba Qwen (DashScope)",
                category="Chinese",
                protocol="openai",
                default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                models_endpoint="/models",
                auth_env_vars=["DASHSCOPE_API_KEY"],
                default_model="alibaba/qwen-max",
                flagship_models=["alibaba/qwen-max", "alibaba/qwen-plus", "alibaba/qwen-turbo", "alibaba/qwen-2.5-coder-32b-instruct"],
                doc_url="https://help.aliyun.com/dashscope",
                description="Alibaba Cloud Qwen 2.5 and Qwen Coder models",
            )
        )
        self.register(
            ProviderProfile(
                id="minimax",
                name="MiniMax",
                category="Chinese",
                protocol="openai",
                default_base_url="https://api.minimax.chat/v1",
                models_endpoint="/v1/models",
                auth_env_vars=["MINIMAX_API_KEY"],
                default_model="minimax/minimax-01",
                flagship_models=["minimax/minimax-01", "minimax/abab6.5s-chat"],
                doc_url="https://api.minimax.chat",
                description="MiniMax abab and text-01 models",
            )
        )
        self.register(
            ProviderProfile(
                id="zhipu",
                name="Zhipu AI (GLM)",
                category="Chinese",
                protocol="openai",
                default_base_url="https://open.bigmodel.cn/api/paas/v4",
                models_endpoint="/models",
                auth_env_vars=["ZHIPU_API_KEY"],
                default_model="zhipu/glm-4",
                flagship_models=["zhipu/glm-4", "zhipu/glm-4-plus", "zhipu/glm-4-air"],
                doc_url="https://open.bigmodel.cn",
                description="Zhipu AI GLM-4 and GLM-4-Plus reasoning models",
            )
        )
        self.register(
            ProviderProfile(
                id="siliconflow",
                name="SiliconFlow",
                category="Chinese",
                protocol="openai",
                default_base_url="https://api.siliconflow.cn/v1",
                models_endpoint="/v1/models",
                auth_env_vars=["SILICONFLOW_API_KEY"],
                default_model="siliconflow/deepseek-ai/DeepSeek-V3",
                flagship_models=[
                    "siliconflow/deepseek-ai/DeepSeek-V3",
                    "siliconflow/deepseek-ai/DeepSeek-R1",
                ],
                doc_url="https://siliconflow.cn",
                description="High-throughput SiliconFlow model API aggregator",
            )
        )

        # Local & Aggregators
        self.register(
            ProviderProfile(
                id="ollama",
                name="Ollama (Local)",
                category="Local",
                protocol="openai",
                default_base_url="http://localhost:11434/v1",
                models_endpoint="/v1/models",
                auth_env_vars=["OLLAMA_API_BASE"],
                default_model="ollama/llama3.2",
                flagship_models=["ollama/llama3.2", "ollama/qwen2.5-coder", "ollama/deepseek-r1"],
                doc_url="https://ollama.com",
                description="Self-hosted local models running via Ollama",
            )
        )
        self.register(
            ProviderProfile(
                id="openrouter",
                name="OpenRouter",
                category="Gateway",
                protocol="openai",
                default_base_url="https://openrouter.ai/api/v1",
                models_endpoint="/v1/models",
                auth_env_vars=["OPENROUTER_API_KEY"],
                default_model="openrouter/anthropic/claude-3.7-sonnet",
                flagship_models=[
                    "openrouter/anthropic/claude-3.7-sonnet",
                    "openrouter/openai/gpt-4o",
                    "openrouter/deepseek/deepseek-r1",
                ],
                doc_url="https://openrouter.ai",
                description="Universal router with access to hundreds of models",
            )
        )


_DEFAULT_REGISTRY: Optional[ProviderRegistry] = None


def get_provider_registry() -> ProviderRegistry:
    """Return the global singleton ProviderRegistry instance."""
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = ProviderRegistry()
    return _DEFAULT_REGISTRY
