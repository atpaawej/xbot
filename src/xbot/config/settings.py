"""Configuration loader for xbot.

Loads environment variables from `.env.local` and `.env` using `python-dotenv`,
with `.env.local` taking precedence. Supports any OpenAI-compatible provider.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


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

    @classmethod
    def load(cls, base_path: Optional[Path] = None) -> Config:
        """Load configuration from environment and .env / .env.local files."""
        loaded = load_env_files(base_path)

        # Flexible resolution for OpenAI-compatible parameters
        base_url = (
            os.getenv("OPENAI_BASE_URL")
            or os.getenv("BASE_URL")
            or "https://api.openai.com/v1"
        ).strip().rstrip("/")

        api_key = (
            os.getenv("OPENAI_API_KEY")
            or os.getenv("API_KEY")
            or ""
        ).strip()

        model_id = (
            os.getenv("MODEL_ID")
            or os.getenv("OPENAI_MODEL_NAME")
            or os.getenv("MODEL_NAME")
            or "gpt-4o"
        ).strip()

        tinyfish_api_key = os.getenv("TINYFISH_API_KEY", "").strip()

        # Workspace directory
        workspace_env = os.getenv("WORKSPACE_DIR", ".")
        workspace_path = (Path(workspace_env) if Path(workspace_env).is_absolute() else (base_path or Path.cwd()) / workspace_env).resolve()

        # Timeout & temperature
        try:
            bash_timeout = int(os.getenv("BASH_TIMEOUT", "120"))
        except ValueError:
            bash_timeout = 120

        try:
            temperature = float(os.getenv("TEMPERATURE", "0.0"))
        except ValueError:
            temperature = 0.0

        return cls(
            base_url=base_url,
            api_key=api_key,
            model_id=model_id,
            tinyfish_api_key=tinyfish_api_key,
            workspace_dir=workspace_path,
            bash_timeout=bash_timeout,
            temperature=temperature,
            loaded_env_files=loaded,
        )

    @property
    def is_llm_configured(self) -> bool:
        """Check if LLM provider has an API key or is a local provider without auth required."""
        # Some local providers (Ollama, local vLLM) may not strictly require a key
        is_local = "localhost" in self.base_url or "127.0.0.1" in self.base_url
        return bool(self.api_key) or is_local

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
        return self._mask_secret(self.api_key)

    @property
    def masked_tinyfish_key(self) -> str:
        return self._mask_secret(self.tinyfish_api_key)


# Global singleton instance
_config_instance: Optional[Config] = None


def set_config(config: Config) -> None:
    """Set the active configuration instance."""
    global _config_instance
    _config_instance = config


def get_config(reload: bool = False, base_path: Optional[Path] = None) -> Config:
    """Get or reload the global configuration instance."""
    global _config_instance
    if _config_instance is None or reload:
        _config_instance = Config.load(base_path)
    return _config_instance
