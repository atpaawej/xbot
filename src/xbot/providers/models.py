"""Data contracts and canonical model parsing for multi-provider architecture."""

from __future__ import annotations

import re
from typing import Any, Optional
from pydantic import BaseModel, Field


def parse_model_ref(raw: str) -> tuple[str, str]:
    """Parse and validate a model string into (provider_id, model_id).

    Enforces strict canonical format 'provider/model_id'.
    Raises ValueError if raw does not conform to 'provider/model_id'.

    Examples:
        >>> parse_model_ref("anthropic/claude-3-7-sonnet-20250219")
        ('anthropic', 'claude-3-7-sonnet-20250219')
        >>> parse_model_ref("openai/gpt-4o")
        ('openai', 'gpt-4o')
        >>> parse_model_ref("deepseek/deepseek-reasoner")
        ('deepseek', 'deepseek-reasoner')
    """
    clean = (raw or "").strip()
    if not clean:
        raise ValueError("Model identifier cannot be empty.")

    if "/" not in clean:
        raise ValueError(
            f"Invalid model format '{clean}'. Models must be specified as 'provider/model_id' "
            "(e.g., 'anthropic/claude-3-7-sonnet-20250219', 'openai/gpt-4o', 'deepseek/deepseek-reasoner')."
        )

    parts = clean.split("/", 1)
    provider = parts[0].strip().lower()
    model_id = parts[1].strip()

    if not provider or not model_id:
        raise ValueError(
            f"Invalid model format '{clean}'. Both provider and model_id must be non-empty."
        )

    return provider, model_id


def canonical_model_id(provider: str, model_id: str) -> str:
    """Construct a canonical 'provider/model_id' string."""
    clean_provider = provider.strip().lower()
    # If model_id already starts with provider + '/', don't duplicate
    clean_model = model_id.strip()
    if clean_model.lower().startswith(f"{clean_provider}/"):
        return clean_model

    clean_model = clean_model.lstrip("/")
    return f"{clean_provider}/{clean_model}"


class ModelInfo(BaseModel):
    """Metadata representation for an LLM model."""

    full_id: str = Field(description="Canonical provider/model_id identifier")
    provider_id: str
    model_id: str
    name: str
    context_window: Optional[int] = None
    max_output: Optional[int] = None
    supports_reasoning: bool = False
    supports_tools: bool = True
    supports_vision: bool = False
    pricing_input: Optional[float] = None
    pricing_output: Optional[float] = None

    @classmethod
    def create(
        cls,
        provider_id: str,
        raw_id: str,
        name: Optional[str] = None,
        **kwargs: Any,
    ) -> ModelInfo:
        clean_p = provider_id.strip().lower()
        full = canonical_model_id(clean_p, raw_id)
        _, mid = parse_model_ref(full)
        display_name = name or mid
        return cls(
            full_id=full,
            provider_id=clean_p,
            model_id=mid,
            name=display_name,
            **kwargs,
        )


class ProviderProfile(BaseModel):
    """Configuration profile for a supported LLM provider."""

    id: str
    name: str
    category: str = "Major"  # Major, Fast/Inference, Chinese, Local, Gateway
    default_base_url: Optional[str] = None
    models_endpoint: Optional[str] = None
    auth_env_vars: list[str] = Field(default_factory=list)
    default_model: str  # Must be canonical 'provider/model_id'
    doc_url: Optional[str] = None
    description: Optional[str] = None


class ProviderAuth(BaseModel):
    """Persisted authentication credentials for a provider."""

    provider_id: str
    api_key: str
    base_url: Optional[str] = None
    default_model: Optional[str] = None  # Canonical 'provider/model_id'
    created_at: Optional[str] = None


class AuthStoreData(BaseModel):
    """Top-level storage schema for ~/.xbot/auth.json."""

    active_model: Optional[str] = None  # Canonical 'provider/model_id'
    providers: dict[str, ProviderAuth] = Field(default_factory=dict)
