"""Multi-provider LLM module for xbot.

Provides canonical provider/model_id resolution, multi-provider credential management,
live model discovery from provider endpoints, and unified LiteLLM streaming protocols.
"""

from __future__ import annotations

from xbot.providers.adapter import LiteLLMProtocol, LiteLLMProvider
from xbot.providers.auth import AuthStore, get_auth_store
from xbot.providers.fetcher import enrich_model_metadata, fetch_provider_models
from xbot.providers.manager import ProviderManager, get_provider_manager
from xbot.providers.models import (
    AuthStoreData,
    ModelInfo,
    ProviderAuth,
    ProviderProfile,
    canonical_model_id,
    parse_model_ref,
)
from xbot.providers.registry import ProviderRegistry, get_provider_registry

__all__ = [
    "canonical_model_id",
    "parse_model_ref",
    "ModelInfo",
    "ProviderProfile",
    "ProviderAuth",
    "AuthStoreData",
    "ProviderRegistry",
    "get_provider_registry",
    "AuthStore",
    "get_auth_store",
    "fetch_provider_models",
    "enrich_model_metadata",
    "LiteLLMProtocol",
    "LiteLLMProvider",
    "ProviderManager",
    "get_provider_manager",
]
