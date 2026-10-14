"""Configuration loader for xbot.

Loads settings hierarchically from:
1. Built-in defaults
2. Global settings.json (~/.xbot/settings.json or $XBOT_DATA_DIR/settings.json)
3. Project settings.json (<workspace>/.xbot/settings.json or <workspace>/settings.json)
4. Environment files (.env, .env.local)
5. Process environment variables ($OPENAI_API_KEY, $MODEL_ID, etc.) and CLI flags
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

KEY_ALIASES: dict[str, str] = {
    "model": "model_id",
    "model_name": "model_id",
    "openai_model_name": "model_id",
    "base_url": "base_url",
    "url": "base_url",
    "openai_base_url": "base_url",
    "api_key": "api_key",
    "key": "api_key",
    "openai_api_key": "api_key",
    "tinyfish_api_key": "tinyfish_api_key",
    "tinyfish_key": "tinyfish_api_key",
    "bash_timeout": "bash_timeout",
    "timeout": "bash_timeout",
    "temperature": "temperature",
    "temp": "temperature",
    "workspace_dir": "workspace_dir",
    "workspace": "workspace_dir",
    "data_dir": "data_dir",
}


def normalize_setting_key(key: str) -> str:
    """Normalize a setting key name using known aliases."""
    clean = key.strip().lower()
    return KEY_ALIASES.get(clean, clean)


def strip_json_comments(text: str) -> str:
    """Strip JavaScript-style single-line (//) and multi-line (/* */) comments from JSON string."""
    pattern = r'(//[^\n]*)|(/\*.*?\*/)|("(?:\\.|[^"\\])*")'

    def replacer(match: re.Match) -> str:
        if match.group(3) is not None:
            return match.group(3)  # String literal, preserve
        return ""  # Comment, remove

    return re.sub(pattern, replacer, text, flags=re.DOTALL)


def strip_trailing_commas(text: str) -> str:
    """Strip trailing commas before closing braces/brackets."""
    return re.sub(r",\s*([}\]])", r"\1", text)


def load_json_file(path: Path) -> dict[str, Any]:
    """Load and parse JSON file supporting JSONC (comments and trailing commas)."""
    if not path.is_file():
        return {}
    try:
        content = path.read_text(encoding="utf-8")
        clean = strip_trailing_commas(strip_json_comments(content))
        if not clean.strip():
            return {}
        data = json.loads(clean)
        if isinstance(data, dict):
            return {normalize_setting_key(k): v for k, v in data.items()}
        return {}
    except Exception:
        return {}


def save_json_file(path: Path, updates: dict[str, Any]) -> None:
    """Save updates to a JSON file, merging with existing keys if file exists."""
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, Any] = {}
    if path.is_file():
        try:
            content = path.read_text(encoding="utf-8")
            clean = strip_trailing_commas(strip_json_comments(content))
            if clean.strip():
                loaded = json.loads(clean)
                if isinstance(loaded, dict):
                    existing = loaded
        except Exception:
            existing = {}

    for k, v in updates.items():
        existing[k] = v

    path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")


def resolve_data_dir(custom_env: Optional[str] = None) -> Path:
    """Resolve global data directory (~/.xbot or XBOT_DATA_DIR)."""
    data_env = custom_env or os.getenv("XBOT_DATA_DIR")
    if data_env:
        return Path(data_env).expanduser().resolve()
    return (Path.home() / ".xbot").resolve()


def get_config_file_paths(
    base_path: Optional[Path | str] = None, data_dir: Optional[Path | str] = None
) -> tuple[Path, Path]:
    """Get the standard global and project settings.json paths.

    Returns:
        (global_settings_path, project_settings_path)
    """
    if data_dir is not None and not isinstance(data_dir, Path):
        try:
            g_dir = Path(data_dir)
        except TypeError:
            g_dir = resolve_data_dir()
    elif isinstance(data_dir, Path):
        g_dir = data_dir
    else:
        g_dir = resolve_data_dir()

    global_path = g_dir / "settings.json"

    if base_path is not None and not isinstance(base_path, Path):
        try:
            root = Path(base_path)
        except TypeError:
            root = Path.cwd()
    elif isinstance(base_path, Path):
        root = base_path
    else:
        root = Path.cwd()

    dot_xbot_file = root / ".xbot" / "settings.json"
    root_file = root / "settings.json"

    # If root/settings.json exists and not .xbot/settings.json, use root/settings.json
    if root_file.is_file() and not dot_xbot_file.is_file():
        project_path = root_file
    else:
        project_path = dot_xbot_file

    return global_path, project_path


def load_env_files(base_path: Optional[Path] = None) -> list[str]:
    """Load .env files with precedence: .env.local > .env.

    Returns the list of loaded file paths.
    """
    root = base_path or Path.cwd()
    loaded_files: list[str] = []

    env_path = root / ".env"
    env_local_path = root / ".env.local"

    # Load .env first if present
    if env_path.is_file():
        load_dotenv(dotenv_path=env_path, override=False)
        loaded_files.append(str(env_path))

    # Load .env.local on top of .env (override=True ensures local takes precedence)
    if env_local_path.is_file():
        load_dotenv(dotenv_path=env_local_path, override=True)
        loaded_files.append(str(env_local_path))

    return loaded_files


@dataclass(frozen=True)
class Config:
    """Runtime configuration for xbot."""

    # OpenAI-compatible Provider settings
    base_url: str
    api_key: str
    model_id: str

    # TinyFish Intelligence settings
    tinyfish_api_key: str

    # Agent execution environment
    workspace_dir: Path
    bash_timeout: int
    temperature: float

    # Metadata
    loaded_env_files: list[str]
    loaded_config_files: list[str] = field(default_factory=list)

    # Global data directory (~/.xbot or XBOT_DATA_DIR)
    data_dir: Path = field(default_factory=lambda: resolve_data_dir())

    # Raw settings dictionary merged from JSON files
    raw_settings: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(
        cls,
        base_path: Optional[Path] = None,
        data_dir: Optional[Path] = None,
    ) -> Config:
        """Load configuration hierarchically from JSON files, .env files, and environment."""
        resolved_data_dir = data_dir or resolve_data_dir()
        root = base_path or Path.cwd()

        # Snapshot process environment before dotenv files are loaded
        proc_env = dict(os.environ)

        # 1. Resolve JSON settings files
        global_path, project_path = get_config_file_paths(base_path=root, data_dir=resolved_data_dir)
        loaded_configs: list[str] = []
        merged_json: dict[str, Any] = {}

        if global_path.is_file():
            g_data = load_json_file(global_path)
            merged_json.update(g_data)
            loaded_configs.append(str(global_path))

        if project_path.is_file():
            p_data = load_json_file(project_path)
            merged_json.update(p_data)
            loaded_configs.append(str(project_path))

        # 2. Load .env and .env.local values to detect file-based env vs process overrides
        from dotenv import dotenv_values
        env_file_values: dict[str, str] = {}
        loaded_envs = load_env_files(root)

        env_path = root / ".env"
        env_local_path = root / ".env.local"
        if env_path.is_file():
            try:
                for k, v in dotenv_values(env_path).items():
                    if v is not None:
                        env_file_values[k] = v
            except Exception:
                pass
        if env_local_path.is_file():
            try:
                for k, v in dotenv_values(env_local_path).items():
                    if v is not None:
                        env_file_values[k] = v
            except Exception:
                pass

        def resolve_setting(
            env_keys: list[str],
            json_key: str,
            default: Any,
        ) -> Any:
            # 1. Explicit shell env or CLI flag present in process env before dotenv
            for k in env_keys:
                if k in proc_env and proc_env[k].strip():
                    return proc_env[k].strip()

            # 2. settings.json (Project or Global)
            if (
                json_key in merged_json
                and merged_json[json_key] is not None
                and str(merged_json[json_key]).strip()
            ):
                return merged_json[json_key]

            # 3. .env / .env.local file values
            for k in env_keys:
                if k in env_file_values and env_file_values[k].strip():
                    return env_file_values[k].strip()

            # 4. Process environment general fallback
            for k in env_keys:
                if k in os.environ and os.environ[k].strip():
                    return os.environ[k].strip()

            # 5. Built-in default
            return default

        # 3. Resolve fields
        raw_base_url = resolve_setting(
            ["OPENAI_BASE_URL", "BASE_URL"], "base_url", "https://api.openai.com/v1"
        )
        base_url = str(raw_base_url).strip().rstrip("/")

        raw_api_key = resolve_setting(
            ["OPENAI_API_KEY", "API_KEY"], "api_key", ""
        )
        api_key = str(raw_api_key).strip()

        # Check auth.json in final_data_dir for active_model
        auth_active_model: Optional[str] = None
        auth_store = None
        try:
            from xbot.providers.auth import AuthStore
            auth_store = AuthStore(final_data_dir / "auth.json")
            auth_active_model = auth_store.get_active_model()
        except Exception:
            auth_active_model = None

        default_model = auth_active_model or "gpt-4o"
        raw_model = resolve_setting(
            ["MODEL_ID", "OPENAI_MODEL_NAME", "MODEL_NAME"], "model_id", default_model
        )
        model_id = str(raw_model).strip()

        # If api_key was not provided, check auth.json for the provider
        if not api_key and auth_store is not None:
            try:
                from xbot.providers.models import parse_model_ref
                if "/" in model_id:
                    p_id, _ = parse_model_ref(model_id)
                    resolved_key, resolved_url = auth_store.resolve_credentials(p_id)
                    if resolved_key:
                        api_key = resolved_key
                    if resolved_url and raw_base_url == "https://api.openai.com/v1":
                        base_url = resolved_url.rstrip("/")
            except Exception:
                pass

        raw_tinyfish = resolve_setting(
            ["TINYFISH_API_KEY"], "tinyfish_api_key", ""
        )
        tinyfish_api_key = str(raw_tinyfish).strip()

        # Workspace directory
        raw_ws = resolve_setting(["WORKSPACE_DIR"], "workspace_dir", ".")
        workspace_env = str(raw_ws).strip()
        workspace_path = (
            Path(workspace_env)
            if Path(workspace_env).is_absolute()
            else (root / workspace_env)
        ).resolve()

        # Global data directory
        raw_data = resolve_setting(["XBOT_DATA_DIR"], "data_dir", None)
        final_data_dir = (
            Path(str(raw_data)).expanduser().resolve()
            if raw_data
            else resolved_data_dir
        )

        # Timeout & temperature
        raw_timeout = resolve_setting(["BASH_TIMEOUT"], "bash_timeout", 120)
        try:
            bash_timeout = int(raw_timeout)
        except (ValueError, TypeError):
            bash_timeout = 120

        raw_temp = resolve_setting(["TEMPERATURE"], "temperature", 0.0)
        try:
            temperature = float(raw_temp)
        except (ValueError, TypeError):
            temperature = 0.0

        return cls(
            base_url=base_url,
            api_key=api_key,
            model_id=model_id,
            tinyfish_api_key=tinyfish_api_key,
            workspace_dir=workspace_path,
            bash_timeout=bash_timeout,
            temperature=temperature,
            loaded_env_files=loaded_envs,
            loaded_config_files=loaded_configs,
            data_dir=final_data_dir,
            raw_settings=merged_json,
        )

    def ensure_data_dir(self) -> Path:
        """Ensure global data directory exists and return it."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir

    @property
    def is_llm_configured(self) -> bool:
        """Check if LLM provider has an API key or is a local provider without auth required."""
        if bool(self.api_key):
            return True
        is_local = "localhost" in self.base_url or "127.0.0.1" in self.base_url
        if is_local:
            return True
        try:
            from xbot.providers.auth import get_auth_store
            from xbot.providers.models import parse_model_ref
            provider, _ = parse_model_ref(self.model_id)
            key, _ = get_auth_store().resolve_credentials(provider)
            return bool(key) or provider == "ollama"
        except Exception:
            return False

    @property
    def is_tinyfish_configured(self) -> bool:
        """Check if TinyFish API key is present."""
        return bool(self.tinyfish_api_key)

    @staticmethod
    def _mask_secret(secret: str) -> str:
        if not secret:
            return "[dim]Not configured[/dim]"
        if len(secret) <= 8:
            return "****"
        return f"{secret[:4]}...{secret[-4:]}"

    @property
    def masked_api_key(self) -> str:
        key = self.api_key
        if not key:
            try:
                from xbot.providers.auth import get_auth_store
                from xbot.providers.models import parse_model_ref
                provider, _ = parse_model_ref(self.model_id)
                key, _ = get_auth_store().resolve_credentials(provider)
            except Exception:
                pass
        return self._mask_secret(key or "")

    @property
    def masked_tinyfish_key(self) -> str:
        return self._mask_secret(self.tinyfish_api_key)


# Global singleton instance
_config_instance: Optional[Config] = None


def set_config(config: Config) -> None:
    """Set the active configuration instance."""
    global _config_instance
    _config_instance = config


def get_config(
    reload: bool = False,
    base_path: Optional[Path] = None,
    data_dir: Optional[Path] = None,
) -> Config:
    """Get or reload the global configuration instance."""
    global _config_instance
    if _config_instance is None or reload:
        _config_instance = Config.load(base_path=base_path, data_dir=data_dir)
    return _config_instance


def update_setting(
    key: str,
    value: Any,
    scope: str = "global",
    base_path: Optional[Path] = None,
    data_dir: Optional[Path] = None,
) -> Config:
    """Update a setting in global or project settings.json and reload configuration.

    Args:
        key: Setting key name (e.g. 'model_id', 'api_key', 'bash_timeout').
        value: Value to set.
        scope: Either 'global' (~/.xbot/settings.json) or 'project' (<workspace>/.xbot/settings.json).
        base_path: Base workspace path (optional).
        data_dir: Global data directory (optional).

    Returns:
        The reloaded Config instance.
    """
    normalized_key = normalize_setting_key(key)
    global_path, project_path = get_config_file_paths(base_path=base_path, data_dir=data_dir)
    target_file = project_path if scope.lower() == "project" else global_path

    # Coerce known types
    converted_val: Any = value
    if normalized_key == "bash_timeout":
        try:
            converted_val = int(value)
        except (ValueError, TypeError):
            pass
    elif normalized_key == "temperature":
        try:
            converted_val = float(value)
        except (ValueError, TypeError):
            pass
    elif isinstance(value, str):
        if value.lower() == "true":
            converted_val = True
        elif value.lower() == "false":
            converted_val = False

    save_json_file(target_file, {normalized_key: converted_val})

    # Clear any lingering environment variables in this process for this setting
    # so that the newly written file value immediately takes effect
    env_keys_to_clear: list[str] = []
    if normalized_key == "model_id":
        env_keys_to_clear.extend(["MODEL_ID", "OPENAI_MODEL_NAME", "MODEL_NAME"])
    elif normalized_key == "base_url":
        env_keys_to_clear.extend(["OPENAI_BASE_URL", "BASE_URL"])
    elif normalized_key == "api_key":
        env_keys_to_clear.extend(["OPENAI_API_KEY", "API_KEY"])
    elif normalized_key == "tinyfish_api_key":
        env_keys_to_clear.append("TINYFISH_API_KEY")
    elif normalized_key == "bash_timeout":
        env_keys_to_clear.append("BASH_TIMEOUT")
    elif normalized_key == "temperature":
        env_keys_to_clear.append("TEMPERATURE")
    elif normalized_key == "workspace_dir":
        env_keys_to_clear.append("WORKSPACE_DIR")

    for k in env_keys_to_clear:
        os.environ.pop(k, None)

    # Reload global configuration instance
    reloaded = Config.load(base_path=base_path, data_dir=data_dir)
    set_config(reloaded)
    return reloaded
