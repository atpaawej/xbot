"""Core Agent module built on the official AI SDK of Python."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Optional, Sequence

from ai import Agent, events, system_message, user_message
from ai.models import InferenceRequestParams, Model, TemperatureSamplerParams
from ai.providers.openai import OpenAIChatCompletionsProtocol, OpenAICompatibleProvider
from ai.types.messages import Message

from xbot.agent.prompts import get_system_prompt
from xbot.config import Config, get_config
from xbot.tools import ALL_TOOLS


# Structured UI/TUI event representations
@dataclass
class AgentTextDelta:
    chunk: str


@dataclass
class AgentReasoningDelta:
    chunk: str


@dataclass
class AgentToolStart:
    tool_name: str
    tool_call_id: str


@dataclass
class AgentToolEnd:
    tool_name: str
    tool_call_id: str
    args: dict[str, Any]


@dataclass
class AgentToolResult:
    tool_name: str
    tool_call_id: str
    result: str
    is_error: bool


@dataclass
class AgentError:
    error_message: str


AgentEvent = (
    AgentTextDelta
    | AgentReasoningDelta
    | AgentToolStart
    | AgentToolEnd
    | AgentToolResult
    | AgentError
)


class AgentManager:
    """Manages the AI SDK Agent, conversation memory, and streaming loop."""

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or get_config()
        from xbot.config import set_config
        set_config(self.config)
        self.provider = OpenAICompatibleProvider(
            name="openai-compatible",
            default_base_url=self.config.base_url,
            api_key_value=self.config.api_key or "not-provided",
            protocol_override=OpenAIChatCompletionsProtocol(),
            headers={},
            env={},
        )
        self.model = Model(id=self.config.model_id, provider=self.provider)
        self.agent = Agent(tools=ALL_TOOLS)
        self.messages: list[Message] = []
        self._init_messages()

    def _init_messages(self) -> None:
        """Initialize or reset messages with the system prompt."""
        self.messages = [
            system_message(get_system_prompt(self.config.workspace_dir))
        ]

    def reset(self) -> None:
        """Reset conversation memory while preserving system configuration."""
        self._init_messages()

    @property
    def turn_count(self) -> int:
        """Count user interaction turns in history."""
        return sum(1 for m in self.messages if getattr(m, "role", None) == "user")

    async def stream_turn(
        self, user_input: str
    ) -> AsyncGenerator[AgentEvent, None]:
        """Stream an agent turn responding to user input.

        Yields fine-grained events for text chunks, tool invocations, and tool results.
        """
        # Validate that an API key is present before initiating request
        if not self.config.is_llm_configured:
            yield AgentError(
                "LLM Provider API key is not configured.\n"
                f"Base URL: {self.config.base_url}\n"
                f"Model ID: {self.config.model_id}\n\n"
                "Please configure OPENAI_API_KEY (or API_KEY) in .env or .env.local.\n"
                "You can copy from .env.example to get started."
            )
            return

        # Append user message
        self.messages.append(user_message(user_input))

        # Setup sampling parameters
        sampler = TemperatureSamplerParams(temperature=self.config.temperature)
        params = InferenceRequestParams(
            sampling={TemperatureSamplerParams: sampler}
        )

        try:
            async with self.agent.run(
                self.model, self.messages, params=params
            ) as stream:
                # Active tracking of tools in progress
                active_tools: dict[str, str] = {}

                async for event in stream:
                    if isinstance(event, events.TextDelta):
                        if event.chunk:
                            yield AgentTextDelta(chunk=event.chunk)

                    elif isinstance(event, events.ReasoningDelta):
                        if event.chunk:
                            yield AgentReasoningDelta(chunk=event.chunk)

                    elif isinstance(event, events.ToolStart):
                        active_tools[event.tool_call_id] = event.tool_name
                        yield AgentToolStart(
                            tool_name=event.tool_name,
                            tool_call_id=event.tool_call_id,
                        )

                    elif isinstance(event, events.ToolEnd):
                        t_name = event.tool_call.tool_name or active_tools.get(
                            event.tool_call_id, "unknown_tool"
                        )
                        args = event.tool_call.tool_args or {}
                        if not isinstance(args, dict):
                            try:
                                args = json.loads(str(args))
                            except Exception:
                                args = {"raw_input": str(args)}
                        yield AgentToolEnd(
                            tool_name=t_name,
                            tool_call_id=event.tool_call_id,
                            args=args,
                        )

                    elif isinstance(event, events.ToolCallResult):
                        for r in event.results:
                            t_name = r.tool_name or active_tools.get(
                                r.tool_call_id, "unknown_tool"
                            )
                            yield AgentToolResult(
                                tool_name=t_name,
                                tool_call_id=r.tool_call_id,
                                result=str(r.result),
                                is_error=bool(r.is_error),
                            )

                # Persist updated conversation trace from the stream
                self.messages = stream.messages

        except Exception as exc:
            err_msg = str(exc)
            yield AgentError(f"Error during agent execution: {err_msg}")
