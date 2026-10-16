"""Abstract base class for LLM wire protocol drivers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Sequence

import pydantic
from ai import types
from ai.models import InferenceRequestParams, Model


class BaseDriver(ABC):
    """Abstract wire protocol driver that streams events conforming to AI SDK."""

    @abstractmethod
    def stream(
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
        """Stream chunks from the upstream LLM and yield normalized AI SDK events."""
        ...
