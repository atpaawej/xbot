"""Dynamic model discovery from provider endpoints, models.dev metadata enrichment, and disk caching."""

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
MODELS_DEV_SPEC_URL = "https://models.dev/models.json"


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


def _get_models_dev_cache() -> dict[str, Any]:
    """Retrieve cached models.dev specification or return empty dict."""
    cache_file = get_cache_dir() / "models_dev_spec.json"
    if cache_file.is_file():
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            cached_time = data.get("timestamp", 0)
            if time.time() - cached_time <= CACHE_TTL_SECONDS:
                return data.get("spec", {})
        except Exception:
            pass

    # Try sync fetch with short timeout if cache missing or expired
    try:
        with httpx.Client(timeout=2.0) as client:
            res = client.get(MODELS_DEV_SPEC_URL)
            if res.status_code == 200:
                spec = res.json()
                cache_file.write_text(
                    json.dumps({"timestamp": time.time(), "spec": spec}),
                    encoding="utf-8",
                )
                return spec
    except Exception:
        pass

    return {}


def enrich_model_metadata(provider_id: str, raw_model_id: str) -> dict[str, Any]:
    """Enrich a model with context window, reasoning support, and specs dynamically."""
    clean_p = provider_id.strip().lower()
    lower_id = raw_model_id.lower()

    meta: dict[str, Any] = {
        "context_window": None,
        "max_output": None,
        "supports_reasoning": False,
        "supports_tools": True,
        "supports_vision": False,
        "pricing_input": None,
        "pricing_output": None,
    }

    # 1. Detect capabilities by naming convention
    if any(k in lower_id for k in ["reasoner", "r1", "o1", "o3", "thinking"]):
        meta["supports_reasoning"] = True

    if any(k in lower_id for k in ["vision", "vl", "omni", "4o", "flash", "claude"]):
        meta["supports_vision"] = True

    # 2. Try models.dev dynamic registry
    spec = _get_models_dev_cache()
    model_spec = None
    for candidate in [
        f"{clean_p}/{raw_model_id}",
        raw_model_id,
        f"{clean_p}:{raw_model_id}",
    ]:
        if candidate in spec:
            model_spec = spec[candidate]
            break

    if model_spec and isinstance(model_spec, dict):
        limit = model_spec.get("limit") or {}
        if isinstance(limit, dict):
            meta["context_window"] = limit.get("context")
            meta["max_output"] = limit.get("output")
        if "reasoning" in model_spec:
            meta["supports_reasoning"] = bool(model_spec["reasoning"])
        if "tool_call" in model_spec:
            meta["supports_tools"] = bool(model_spec["tool_call"])
        cost = model_spec.get("cost") or {}
        if isinstance(cost, dict):
            meta["pricing_input"] = cost.get("input")
            meta["pricing_output"] = cost.get("output")

    # 3. Try modelsdotdev package if context window still missing
    if not meta["context_window"]:
        try:
            import modelsdotdev

            m_dev = modelsdotdev.get_model_by_id(f"{clean_p}:{raw_model_id}")
            if m_dev and m_dev.limits:
                meta["context_window"] = m_dev.limits.context
                meta["max_output"] = m_dev.limits.output
        except Exception:
            pass

    # 4. Fallback defaults if still unspecified
    if not meta["context_window"]:
        if "claude" in lower_id:
            meta["context_window"] = 200000
            meta["max_output"] = 64000
        elif "gpt-4" in lower_id or "o1" in lower_id or "o3" in lower_id:
            meta["context_window"] = 128000
            meta["max_output"] = 16384
        elif "gemini" in lower_id:
            meta["context_window"] = 1000000
            meta["max_output"] = 8192
        elif "deepseek" in lower_id:
            meta["context_window"] = 64000
            meta["max_output"] = 8192
        else:
            meta["context_window"] = 128000
            meta["max_output"] = 8192

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

        endpoint_url = target_base.rstrip("/") + (
            profile.models_endpoint if profile and profile.models_endpoint else "/models"
        )

        # Specific Anthropic models URL
        if clean_p == "anthropic":
            endpoint_url = "https://api.anthropic.com/v1/models"

        # Specific Ollama discovery
        if clean_p == "ollama":
            endpoint_url = target_base.rstrip("/v1").rstrip("/") + "/api/tags"

        # Specific OpenRouter discovery
        if clean_p == "openrouter":
            endpoint_url = "https://openrouter.ai/api/v1/models"

        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                res = await client.get(endpoint_url, headers=headers)
                if res.status_code == 200:
                    payload = res.json()
                    # Standard OpenAI / OpenRouter format: {"data": [{"id": "gpt-4o"}, ...]}
                    if "data" in payload and isinstance(payload["data"], list):
                        for item in payload["data"]:
                            if isinstance(item, dict) and "id" in item:
                                raw_model_ids.append(str(item["id"]))
                    # Ollama / Anthropic format: {"models": [...]}
                    elif "models" in payload and isinstance(payload["models"], list):
                        for item in payload["models"]:
                            if isinstance(item, dict):
                                m_id = item.get("name") or item.get("id") or item.get("model")
                                if m_id:
                                    raw_model_ids.append(str(m_id))
        except Exception:
            pass

    # 2. Fallback to profile's flagship models if endpoint didn't return any
    if not raw_model_ids and profile and profile.flagship_models:
        for fm in profile.flagship_models:
            _, mid = parse_model_ref(fm)
            raw_model_ids.append(mid)

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

    # Sort models: default model first, then alphabetical
    def sort_key(m: ModelInfo) -> tuple[int, str]:
        is_default = profile and m.full_id == profile.default_model
        return (0 if is_default else 1, m.full_id)

    models.sort(key=sort_key)

    if models:
        _save_cached_models(clean_p, models)

    return models
