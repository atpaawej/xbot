"""Secure multi-provider authentication store (~/.xbot/auth.json)."""

from __future__ import annotations

import json
import os
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from xbot.providers.models import (
    AuthStoreData,
    ProviderAuth,
    canonical_model_id,
    parse_model_ref,
)
from xbot.providers.registry import get_provider_registry


def resolve_auth_file_path() -> Path:
    """Resolve standard auth.json path (~/.xbot/auth.json or $XBOT_DATA_DIR/auth.json)."""
    data_env = os.getenv("XBOT_DATA_DIR")
    if data_env:
        base = Path(data_env).expanduser().resolve()
    else:
        base = (Path.home() / ".xbot").resolve()
    return base / "auth.json"


class AuthStore:
    """Thread-safe and process-safe manager for ~/.xbot/auth.json."""

    def __init__(self, file_path: Optional[Path] = None) -> None:
        self.file_path = file_path or resolve_auth_file_path()

    def load(self) -> AuthStoreData:
        """Load auth data from disk with error recovery."""
        if not self.file_path.is_file():
            return AuthStoreData()

        try:
            content = self.file_path.read_text(encoding="utf-8")
            if not content.strip():
                return AuthStoreData()
            data = json.loads(content)
            return AuthStoreData.model_validate(data)
        except Exception:
            return AuthStoreData()

    def save(self, data: AuthStoreData) -> None:
        """Persist auth data atomically with 0600 permissions."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        # Ensure parent directory is at least 0700
        try:
            os.chmod(self.file_path.parent, stat.S_IRWXU)
        except OSError:
            pass

        content = data.model_dump_json(indent=2) + "\n"

        # Atomic write via temporary file in same directory
        temp_fd, temp_path = tempfile.mkstemp(
            dir=str(self.file_path.parent),
            prefix="auth_",
            suffix=".tmp",
        )
        try:
            with open(temp_fd, "w", encoding="utf-8") as f:
                f.write(content)
            # Enforce 0600 on created temp file
            os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR)
            # Atomically replace target file
            os.replace(temp_path, str(self.file_path))
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

    def save_provider_auth(
        self,
        provider_id: str,
        api_key: str,
        default_model: Optional[str] = None,
        base_url: Optional[str] = None,
        set_as_active: bool = True,
    ) -> None:
        """Store credentials for a provider and optionally activate its default model."""
        clean_p = provider_id.strip().lower()
        clean_key = api_key.strip()

        # Enforce canonical model ID format if provided
        canonical_model = None
        if default_model:
            canonical_model = canonical_model_id(clean_p, default_model)
            parse_model_ref(canonical_model)  # validates

        data = self.load()
        existing = data.providers.get(clean_p)

        now_str = datetime.now(timezone.utc).isoformat()
        auth_entry = ProviderAuth(
            provider_id=clean_p,
            api_key=clean_key,
            base_url=base_url.strip() if base_url else (existing.base_url if existing else None),
            default_model=canonical_model or (existing.default_model if existing else None),
            created_at=existing.created_at if existing and existing.created_at else now_str,
        )

        data.providers[clean_p] = auth_entry
        if set_as_active and canonical_model:
            data.active_model = canonical_model

        self.save(data)

    def remove_provider_auth(self, provider_id: str) -> bool:
        """Remove a provider's credentials from auth.json."""
        clean_p = provider_id.strip().lower()
        data = self.load()
        if clean_p in data.providers:
            del data.providers[clean_p]
            # If active model was from this provider, reset active_model
            if data.active_model and data.active_model.startswith(f"{clean_p}/"):
                data.active_model = None
            self.save(data)
            return True
        return False

    def set_active_model(self, canonical_model: str) -> None:
        """Set the globally active canonical model."""
        parse_model_ref(canonical_model)  # validates strict provider/model_id
        data = self.load()
        data.active_model = canonical_model
        self.save(data)

    def get_active_model(self) -> Optional[str]:
        """Return the currently configured active canonical model."""
        return self.load().active_model

    def get_authenticated_providers(self) -> list[str]:
        """Return all provider IDs currently authenticated via auth.json or environment."""
        registry = get_provider_registry()
        authenticated: set[str] = set()

        # 1. From auth.json
        data = self.load()
        for p_id, p_auth in data.providers.items():
            if p_auth.api_key:
                authenticated.add(p_id)

        # 2. From environment variables
        for profile in registry.all_providers():
            for env_var in profile.auth_env_vars:
                val = os.getenv(env_var)
                if val and val.strip():
                    authenticated.add(profile.id)
                    break

        # Ollama is always accessible locally without mandatory key
        authenticated.add("ollama")

        return sorted(list(authenticated))

    def resolve_credentials(
        self, provider_id: str
    ) -> tuple[Optional[str], Optional[str]]:
        """Resolve (api_key, base_url) with precedence: auth.json > environment > defaults.

        Returns:
            (api_key, base_url)
        """
        clean_p = provider_id.strip().lower()
        registry = get_provider_registry()
        profile = registry.get(clean_p)

        api_key: Optional[str] = None
        base_url: Optional[str] = None

        # 1. Check auth.json
        data = self.load()
        p_auth = data.providers.get(clean_p)
        if p_auth:
            if p_auth.api_key:
                api_key = p_auth.api_key
            if p_auth.base_url:
                base_url = p_auth.base_url

        # 2. Check environment variables if api_key not found in auth.json
        if not api_key and profile:
            for env_var in profile.auth_env_vars:
                val = os.getenv(env_var)
                if val and val.strip():
                    api_key = val.strip()
                    break

        # 3. Check base_url fallback from profile or env
        if not base_url and profile:
            base_url = profile.default_base_url

        return api_key, base_url


_DEFAULT_AUTH_STORE: Optional[AuthStore] = None


def get_auth_store() -> AuthStore:
    """Return the global AuthStore singleton."""
    global _DEFAULT_AUTH_STORE
    if _DEFAULT_AUTH_STORE is None:
        _DEFAULT_AUTH_STORE = AuthStore()
    return _DEFAULT_AUTH_STORE
