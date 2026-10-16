"""High-level ProviderManager coordinating model instantiation and runtime switching."""

from __future__ import annotations

import os
from typing import Optional

from ai.models import Model

from xbot.providers.adapter import (
    LiteLLMProtocol,
    LiteLLMProvider,
    MultiProvider,
    MultiProviderProtocol,
)
from xbot.providers.auth import AuthStore, get_auth_store
from xbot.providers.fetcher import fetch_provider_models
from xbot.providers.models import ModelInfo, canonical_model_id, parse_model_ref
from xbot.providers.registry import ProviderRegistry, get_provider_registry


class ProviderManager:
    """Manages active provider/model selection, instantiation, and credential binding."""

    def __init__(
        self,
        auth_store: Optional[AuthStore] = None,
        registry: Optional[ProviderRegistry] = None,
        initial_model: Optional[str] = None,
    ) -> None:
        self.auth_store = auth_store or get_auth_store()
        self.registry = registry or get_provider_registry()

        # Resolve initial canonical model
        active_from_store = self.auth_store.get_active_model()
        if initial_model:
            provider, mid = parse_model_ref(initial_model)
            self._active_model = canonical_model_id(provider, mid)
        elif active_from_store:
            self._active_model = active_from_store
        else:
            self._active_model = "openai/gpt-4o"

    @property
    def active_model(self) -> str:
        """Return the current canonical model identifier (e.g. 'anthropic/claude-3-7-sonnet-20250219')."""
        return self._active_model

    @property
    def active_provider_id(self) -> str:
        """Return the active provider ID extracted from the active canonical model."""
        provider, _ = parse_model_ref(self._active_model)
        return provider

    def switch_model(self, canonical_model: str, persist: bool = True) -> str:
        """Switch active model and provider at runtime.

        Raises ValueError if canonical_model does not adhere to 'provider/model_id'.
        """
        provider, mid = parse_model_ref(canonical_model)
        formatted = canonical_model_id(provider, mid)

        self._active_model = formatted
        if persist:
            self.auth_store.set_active_model(formatted)

        return formatted

    def create_model(
        self,
        canonical_model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Model:
        """Instantiate an AI SDK Model configured with the LiteLLM adapter.

        Guarantees that credentials from auth.json/environment are bound.
        """
        raw_target = canonical_model or self._active_model
        if "/" not in raw_target:
            target_model = f"openai/{raw_target}"
        else:
            target_model = raw_target

        provider_id, model_id = parse_model_ref(target_model)
        clean_full_id = canonical_model_id(provider_id, model_id)

        # Resolve credentials (explicit parameters take highest precedence)
        resolved_key, resolved_url = self.auth_store.resolve_credentials(provider_id)
        final_key = api_key if (api_key is not None and api_key != "") else resolved_key
        final_url = base_url if (base_url is not None and base_url != "") else resolved_url
        if not final_url:
            final_url = "https://api.openai.com/v1"

        # Create LiteLLM Provider instance
        provider_instance = LiteLLMProvider(
            name=provider_id,
            default_base_url=final_url,
            api_key_value=final_key or "not-provided",
            headers={},
            env={},
        )

        protocol = LiteLLMProtocol()

        # If original target was a specific raw ID without provider (e.g. in test), preserve it
        active_id = canonical_model if (canonical_model and "/" not in canonical_model) else clean_full_id

        return Model(
            id=active_id,
            provider=provider_instance,
            protocol=protocol,
        )

    async def list_available_models(
        self, force_refresh: bool = False
    ) -> list[ModelInfo]:
        """Fetch and return available models across all currently authenticated providers.

        All models have full_id formatted as 'provider/model_id'.
        """
        authenticated_providers = self.auth_store.get_authenticated_providers()
        all_models: list[ModelInfo] = []

        for p_id in authenticated_providers:
            api_key, base_url = self.auth_store.resolve_credentials(p_id)
            try:
                p_models = await fetch_provider_models(
                    provider_id=p_id,
                    api_key=api_key,
                    base_url=base_url,
                    force_refresh=force_refresh,
                )
                all_models.extend(p_models)
            except Exception:
                continue

        return all_models


_DEFAULT_MANAGER: Optional[ProviderManager] = None


def get_provider_manager() -> ProviderManager:
    """Return the global ProviderManager singleton."""
    global _DEFAULT_MANAGER
    if _DEFAULT_MANAGER is None:
        _DEFAULT_MANAGER = ProviderManager()
    return _DEFAULT_MANAGER
