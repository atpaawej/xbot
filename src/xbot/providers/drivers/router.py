"""Driver registry and routing for LLM wire protocols."""

from __future__ import annotations

from typing import Optional
from xbot.providers.drivers.anthropic_driver import AnthropicDriver
from xbot.providers.drivers.base import BaseDriver
from xbot.providers.drivers.openai_driver import OpenAICompatibleDriver

_DRIVERS: dict[str, BaseDriver] = {
    "openai": OpenAICompatibleDriver(),
    "anthropic": AnthropicDriver(),
}


def register_driver(protocol_name: str, driver: BaseDriver) -> None:
    """Register or override a wire protocol driver."""
    _DRIVERS[protocol_name.strip().lower()] = driver


def get_driver(protocol_name: str) -> BaseDriver:
    """Retrieve driver for protocol name, defaulting to OpenAI-compatible driver."""
    clean = (protocol_name or "").strip().lower()
    return _DRIVERS.get(clean, _DRIVERS["openai"])
