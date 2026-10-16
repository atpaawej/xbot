"""Native multi-provider adapter bridging raw SDK streaming into the Python AI SDK."""

from __future__ import annotations

from typing import Any, AsyncGenerator, ClassVar, Literal, Optional, Sequence

import pydantic
from ai import types
from ai.models import InferenceRequestParams, Model
from ai.providers import base

from xbot.providers.drivers import get_driver
from xbot.providers.models import parse_model_ref
from xbot.providers.registry import get_provider_registry


class MultiProviderProtocol(base.ProviderProtocol[Any]):
    """AI SDK ProviderProtocol that dynamically routes streaming to raw wire drivers."""

    protocol_class_id: Literal["multi_provider"] = "multi_provider"

    async def stream(
        self,
        client: Any,
        model: Model,
        messages: list[types.messages.Message],
        *,
        tools: Sequence[types.tools.Tool] | None = None,
        output_type: type[pydantic.BaseModel] | None = None,
        params: InferenceRequestParams | None = None,
        provider: str,
    ) -> AsyncGenerator[types.events.Event]:
        """Route completion streaming through the appropriate protocol driver."""
        if "/" in model.id:
            provider_name, _ = parse_model_ref(model.id)
        else:
            provider_name = getattr(model.provider, "name", "openai") or "openai"

        # Determine wire protocol from registry profile
        registry = get_provider_registry()
        profile = registry.get(provider_name)
        protocol_name = (
            getattr(profile, "protocol", "openai")
            if profile
            else ("anthropic" if provider_name == "anthropic" else "openai")
        )

        driver = get_driver(protocol_name)

        async for event in driver.stream(
            client=client,
            model=model,
            messages=messages,
            tools=tools,
            output_type=output_type,
            params=params,
            provider=provider_name,
        ):
            yield event


class MultiProvider(base.Provider[Any]):
    """AI SDK Provider implementation wrapping raw SDK clients."""

    handles: ClassVar[tuple[str, ...]] = ("multi_provider", "litellm")
    provider_class_id: Literal["multi_provider"] = "multi_provider"

    @property
    def client(self) -> Any:
        """Create or return raw SDK client instance based on configured provider."""
        registry = get_provider_registry()
        profile = registry.get(self.name)
        protocol_name = (
            getattr(profile, "protocol", "openai")
            if profile
            else ("anthropic" if self.name == "anthropic" else "openai")
        )

        if protocol_name == "anthropic":
            import anthropic

            base_u = self.base_url
            return anthropic.AsyncAnthropic(
                api_key=self.api_key or "no-key",
                base_url=str(base_u) if base_u else None,
            )
        else:
            import openai

            base_u = self.base_url or (profile.default_base_url if profile else "https://api.openai.com/v1")
            return openai.AsyncOpenAI(
                api_key=self.api_key or "no-key",
                base_url=str(base_u),
            )

    def default_protocol(self) -> base.ProviderProtocol[Any]:
        """Return the multi-provider protocol instance."""
        return MultiProviderProtocol()

    def is_configured(self) -> bool:
        """Provider is configured if an API key exists or for local Ollama."""
        if self.name == "ollama":
            return True
        return bool(self.api_key)


# Aliases for backward compatibility across existing tests and imports
LiteLLMProtocol = MultiProviderProtocol
LiteLLMProvider = MultiProvider
