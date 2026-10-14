"""LiteLLM adapter bridging multi-provider streaming into the Python AI SDK."""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator, ClassVar, Literal, Mapping, Optional, Sequence

import litellm
import pydantic
from ai import types
from ai.models import Model, InferenceRequestParams
from ai.providers import base
from ai.providers.openai.protocol import _messages_to_openai, _tools_to_openai, _FINISH_REASONS

from xbot.providers.models import parse_model_ref


class LiteLLMProtocol(base.ProviderProtocol[Any]):
    """AI SDK ProviderProtocol that routes completion streams through LiteLLM."""

    protocol_class_id: Literal["litellm"] = "litellm"

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
        """Stream response chunks from LiteLLM and normalize into AI SDK events."""
        # Validate and resolve canonical model identifier
        if "/" in model.id:
            provider_name, raw_model_id = parse_model_ref(model.id)
            litellm_model = model.id
        else:
            provider_name = getattr(model.provider, "name", "openai")
            raw_model_id = model.id
            litellm_model = f"openai/{raw_model_id}"

        # Prepare messages and tools for OpenAI/LiteLLM schema
        openai_messages = await _messages_to_openai(messages)
        openai_tools = _tools_to_openai(tools) if tools else None

        # Resolve credentials from provider attached to model
        api_key = getattr(model.provider, "api_key", None)
        base_url = getattr(model.provider, "base_url", None)

        kwargs: dict[str, Any] = {
            "model": model.id,
            "messages": openai_messages,
            "stream": True,
        }

        if openai_tools:
            kwargs["tools"] = openai_tools

        if api_key:
            kwargs["api_key"] = api_key

        # If custom base_url specified (e.g. Ollama, mock server, custom proxy)
        if base_url:
            kwargs["api_base"] = base_url
            kwargs["base_url"] = base_url
            if (
                provider_name in ["openai", "custom"]
                or "localhost" in base_url
                or "127.0.0.1" in base_url
                or not litellm.check_valid_key(model=litellm_model, api_key=api_key or "")
            ):
                kwargs["custom_llm_provider"] = "openai"

        # Apply sampling params if provided
        if params is not None:
            # Temperature
            for param_key, param_val in getattr(params, "sampling", {}).items():
                if hasattr(param_val, "temperature") and param_val.temperature is not None:
                    kwargs["temperature"] = param_val.temperature
                    break

        try:
            sdk_stream = await litellm.acompletion(**kwargs)
        except Exception as exc:
            raise RuntimeError(f"LiteLLM error for model '{model.id}': {exc}") from exc

        text_started = False
        reasoning_started = False
        tc_state: dict[int, dict[str, Any]] = {}
        usage: Optional[types.usage.Usage] = None
        finish_reason: Optional[str] = None
        raw_finish_reason: Optional[str] = None
        response_id: Optional[str] = None
        response_model: Optional[str] = model.id

        yield types.events.StreamStart()

        try:
            async for chunk in sdk_stream:
                if getattr(chunk, "id", None):
                    response_id = chunk.id
                if getattr(chunk, "model", None):
                    response_model = chunk.model

                # Track token usage if provided in chunk
                chunk_usage = getattr(chunk, "usage", None)
                if chunk_usage is not None:
                    raw_usage = (
                        chunk_usage.model_dump(exclude_none=True)
                        if hasattr(chunk_usage, "model_dump")
                        else dict(chunk_usage)
                    )
                    reasoning_tokens: Optional[int] = None
                    cd = getattr(chunk_usage, "completion_tokens_details", None)
                    if cd:
                        reasoning_tokens = getattr(cd, "reasoning_tokens", None)
                    usage = types.usage.Usage(
                        input_tokens=getattr(chunk_usage, "prompt_tokens", 0) or 0,
                        output_tokens=getattr(chunk_usage, "completion_tokens", 0) or 0,
                        reasoning_tokens=reasoning_tokens,
                        raw=raw_usage,
                    )

                if not getattr(chunk, "choices", None):
                    continue

                choice = chunk.choices[0]
                delta = getattr(choice, "delta", None)
                if delta is None:
                    continue

                # Reasoning delta extraction (DeepSeek R1, o1, Claude Thinking)
                reasoning_chunk = (
                    getattr(delta, "reasoning_content", None)
                    or getattr(delta, "reasoning", None)
                    or getattr(delta, "thinking", None)
                )
                if reasoning_chunk:
                    if not reasoning_started:
                        reasoning_started = True
                        yield types.events.ReasoningStart(block_id="reasoning")
                    yield types.events.ReasoningDelta(
                        chunk=reasoning_chunk, block_id="reasoning"
                    )

                # Standard text delta extraction
                content_chunk = getattr(delta, "content", None)
                if content_chunk:
                    if reasoning_started:
                        yield types.events.ReasoningEnd(block_id="reasoning")
                        reasoning_started = False

                    if not text_started:
                        text_started = True
                        yield types.events.TextStart(block_id="text")
                    yield types.events.TextDelta(
                        chunk=content_chunk, block_id="text"
                    )

                # Tool call deltas
                tool_calls = getattr(delta, "tool_calls", None)
                if tool_calls:
                    for tc in tool_calls:
                        idx = getattr(tc, "index", 0)
                        if idx not in tc_state:
                            tc_state[idx] = {
                                "id": getattr(tc, "id", None) or f"call_{idx}",
                                "name": None,
                                "arguments": "",
                                "started": False,
                            }
                        if getattr(tc, "id", None):
                            tc_state[idx]["id"] = tc.id

                        fn = getattr(tc, "function", None)
                        if fn:
                            if getattr(fn, "name", None):
                                tc_state[idx]["name"] = fn.name
                            if getattr(fn, "arguments", None):
                                tc_state[idx]["arguments"] += fn.arguments
                                tid = tc_state[idx]["id"]
                                tname = tc_state[idx]["name"] or ""

                                if not tc_state[idx]["started"] and tid:
                                    tc_state[idx]["started"] = True
                                    yield types.events.ToolStart(
                                        tool_call_id=tid,
                                        tool_name=tname,
                                    )

                                if tid:
                                    yield types.events.ToolDelta(
                                        chunk=fn.arguments,
                                        tool_call_id=tid,
                                    )

                # Finish reason handling
                fn_reason = getattr(choice, "finish_reason", None)
                if fn_reason is not None:
                    raw_finish_reason = fn_reason
                    finish_reason = _FINISH_REASONS.get(fn_reason, "other")
                    if reasoning_started:
                        yield types.events.ReasoningEnd(block_id="reasoning")
                        reasoning_started = False
                    if text_started:
                        yield types.events.TextEnd(block_id="text")
                        text_started = False
                    for tc_info in tc_state.values():
                        if tc_info["started"] and tc_info["id"]:
                            call_part = types.messages.ToolCallPart(
                                tool_call_id=tc_info["id"],
                                tool_name=tc_info["name"] or "",
                                tool_args=tc_info["arguments"],
                            )
                            yield types.events.ToolEnd(
                                tool_call_id=tc_info["id"],
                                tool_call=call_part,
                            )
                            tc_info["started"] = False

            # Cleanup open blocks if not closed
            if reasoning_started:
                yield types.events.ReasoningEnd(block_id="reasoning")
            if text_started:
                yield types.events.TextEnd(block_id="text")
            for tc_info in tc_state.values():
                if tc_info["started"] and tc_info["id"]:
                    call_part = types.messages.ToolCallPart(
                        tool_call_id=tc_info["id"],
                        tool_name=tc_info["name"] or "",
                        tool_args=tc_info["arguments"],
                    )
                    yield types.events.ToolEnd(
                        tool_call_id=tc_info["id"],
                        tool_call=call_part,
                    )

            yield types.events.StreamEnd(
                usage=usage,
                finish_reason=finish_reason or "stop",
                response_id=response_id,
                response_model=response_model,
            )
        except Exception as exc:
            raise RuntimeError(f"Error streaming model '{model.id}': {exc}") from exc


class LiteLLMProvider(base.Provider[Any]):
    """AI SDK Provider implementation wrapping LiteLLM."""

    handles: ClassVar[tuple[str, ...]] = ("litellm",)
    provider_class_id: Literal["litellm"] = "litellm"

    @property
    def client(self) -> Any:
        """Dummy client for Provider protocol requirements."""
        return object()

    def default_protocol(self) -> base.ProviderProtocol[Any]:
        """Return the singleton LiteLLM protocol."""
        return LiteLLMProtocol()

    def is_configured(self) -> bool:
        """Provider is configured if an API key exists or for local Ollama."""
        if self.name == "ollama":
            return True
        return bool(self.api_key)
