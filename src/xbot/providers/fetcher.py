"""Dynamic model discovery from provider endpoints, metadata enrichment, and disk caching."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Optional

import httpx

from xbot.providers.models import ModelInfo, canonical_model_id, parse_model_ref
from xbot.providers.registry import get_provider_registry

CACHE_TTL_SECONDS = 86400  # 24 hours


def get_cache_dir() -> Path:
    """Resolve model cache directory (~/.xbot/cache)."""
    data_env = os.getenv("XBOT_DATA_DIR")
    if data_env:
        base = Path(data_env).expanduser().resolve()
    else:
        base = (Path.home() / ".xbot").resolve()
    cache_path = base / "cache"
    cache_path.mkdir(parents=True, exist_ok=True)
    return cache_path


def _load_cached_models(provider_id: str) -> Optional[list[ModelInfo]]:
    """Load cached model list for a provider if not expired."""
    cache_file = get_cache_dir() / f"models_{provider_id}.json"
    if not cache_file.is_file():
        return None

    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        cached_time = data.get("timestamp", 0)
        if time.time() - cached_time > CACHE_TTL_SECONDS:
            return None

        models_raw = data.get("models", [])
        return [ModelInfo.model_validate(m) for m in models_raw]
    except Exception:
        return None


def _save_cached_models(provider_id: str, models: list[ModelInfo]) -> None:
    """Save model list to disk cache."""
    cache_file = get_cache_dir() / f"models_{provider_id}.json"
    try:
        data = {
            "timestamp": time.time(),
            "provider_id": provider_id,
            "models": [m.model_dump() for m in models],
        }
        cache_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    except Exception:
        pass


def enrich_model_metadata(provider_id: str, raw_model_id: str) -> dict[str, Any]:
    """Enrich a model with context window, reasoning support, and specs using LiteLLM/modelsdotdev."""
    clean_p = provider_id.strip().lower()
    full_id = canonical_model_id(clean_p, raw_model_id)

    meta: dict[str, Any] = {
        "context_window": None,
        "max_output": None,
        "supports_reasoning": False,
        "supports_tools": True,
        "supports_vision": False,
        "pricing_input": None,
        "pricing_output": None,
    }

    # Detect reasoning capability by naming convention
    lower_id = raw_model_id.lower()
    if any(k in lower_id for k in ["reasoner", "r1", "o1", "o3", "thinking"]):
        meta["supports_reasoning"] = True

    # 1. Try LiteLLM model info
    try:
        import litellm
        info = None
        for candidate in [full_id, raw_model_id]:
            try:
                info = litellm.get_model_info(candidate)
                if info:
                    break
            except Exception:
                continue

        if info:
            meta["context_window"] = info.get("max_input_tokens") or info.get("max_tokens")
            meta["max_output"] = info.get("max_output_tokens")
            if info.get("supports_function_calling") is not None:
                meta["supports_tools"] = bool(info.get("supports_function_calling"))
            if info.get("supports_vision") is not None:
                meta["supports_vision"] = bool(info.get("supports_vision"))
            meta["pricing_input"] = info.get("input_cost_per_token")
            meta["pricing_output"] = info.get("output_cost_per_token")
            if info.get("supports_reasoning") is not None:
                meta["supports_reasoning"] = bool(info.get("supports_reasoning"))
    except Exception:
        pass

    # 2. Try modelsdotdev enrichment if context window still missing
    if not meta["context_window"]:
        try:
            import modelsdotdev
            m_dev = modelsdotdev.get_model_by_id(f"{clean_p}:{raw_model_id}")
            if m_dev and m_dev.limits:
                meta["context_window"] = m_dev.limits.context
                meta["max_output"] = m_dev.limits.output
        except Exception:
            pass

    return meta


async def fetch_provider_models(
    provider_id: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    force_refresh: bool = False,
    timeout: float = 8.0,
) -> list[ModelInfo]:
    """Fetch available models dynamically from provider endpoint.

    All returned models have full_id formatted canonically as 'provider/model_id'.
    """
    clean_p = provider_id.strip().lower()

    if not force_refresh:
        cached = _load_cached_models(clean_p)
        if cached:
            return cached

    registry = get_provider_registry()
    profile = registry.get(clean_p)
    target_base = base_url or (profile.default_base_url if profile else None)

    raw_model_ids: list[str] = []

    # 1. Query live endpoint via HTTP
    if target_base:
        headers: dict[str, str] = {}
        if api_key and api_key.strip():
            if clean_p == "anthropic":
                headers["x-api-key"] = api_key.strip()
                headers["anthropic-version"] = "2023-06-01"
            else:
                headers["Authorization"] = f"Bearer {api_key.strip()}"

        endpoint_url = target_base.rstrip("/") + (profile.models_endpoint if profile and profile.models_endpoint else "/models")

        # Specific Anthropic models URL
        if clean_p == "anthropic":
            endpoint_url = "https://api.anthropic.com/v1/models"

        # Specific Ollama discovery
        if clean_p == "ollama":
            endpoint_url = target_base.rstrip("/v1").rstrip("/") + "/api/tags"

        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                res = await client.get(endpoint_url, headers=headers)
                if res.status_code == 200:
                    payload = res.json()
                    # Standard OpenAI format: {"data": [{"id": "gpt-4o"}, ...]}
                    if "data" in payload and isinstance(payload["data"], list):
                        for item in payload["data"]:
                            if isinstance(item, dict) and "id" in item:
                                raw_model_ids.append(str(item["id"]))
                    # Anthropic format: {"data": [{"id": "..."}, ...]}
                    elif "models" in payload and isinstance(payload["models"], list):
                        # Ollama format: {"models": [{"name": "llama3.2:latest"}, ...]}
                        for item in payload["models"]:
                            if isinstance(item, dict):
                                m_id = item.get("name") or item.get("id") or item.get("model")
                                if m_id:
                                    raw_model_ids.append(str(m_id))
        except Exception:
            pass

    # 2. Fallback to LiteLLM's known models catalog if endpoint didn't return any
    if not raw_model_ids:
        try:
            import litellm
            # Provider mapping in LiteLLM
            litellm_p = "xai" if clean_p == "xai" else clean_p
            known = litellm.models_by_provider.get(litellm_p, [])
            for k in known:
                raw_model_ids.append(str(k))
        except Exception:
            pass

    # 3. Fallback to profile default model if still empty
    if not raw_model_ids and profile:
        _, mid = parse_model_ref(profile.default_model)
        raw_model_ids.append(mid)

    # 4. Construct ModelInfo items with canonical provider/model_id
    models: list[ModelInfo] = []
    seen: set[str] = set()

    for r_id in raw_model_ids:
        clean_raw = r_id.strip()
        # Strip provider prefix if raw already contains it
        if clean_raw.lower().startswith(f"{clean_p}/"):
            clean_raw = clean_raw[len(clean_p) + 1 :]

        full = canonical_model_id(clean_p, clean_raw)
        if full in seen:
            continue
        seen.add(full)

        meta = enrich_model_metadata(clean_p, clean_raw)
        models.append(
            ModelInfo.create(
                provider_id=clean_p,
                raw_id=clean_raw,
                name=clean_raw,
                **meta,
            )
        )

    # Sort models: default/flagship models first, then alphabetical
    def sort_key(m: ModelInfo) -> tuple[int, str]:
        is_default = profile and m.full_id == profile.default_model
        return (0 if is_default else 1, m.full_id)

    models.sort(key=sort_key)

    if models:
        _save_cached_models(clean_p, models)

    return models
