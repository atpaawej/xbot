"""OpenAI-compatible wire protocol driver using raw openai.AsyncOpenAI."""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Sequence

import openai
import pydantic
from ai import types
from ai.models import InferenceRequestParams, Model
from ai.providers.openai.protocol import (
    _FINISH_REASONS,
    _apply_common_openai_params,
    _coerce_params,
    _messages_to_openai,
    _tools_to_openai,
)

from xbot.providers.drivers.base import BaseDriver
from xbot.providers.models import parse_model_ref


class OpenAICompatibleDriver(BaseDriver):
    """Driver executing completions against OpenAI-compatible REST/SSE APIs."""

    def _resolve_wire_model(self, model_id: str, provider: str) -> str:
        """Resolve the raw model string expected by the remote provider."""
        if "/" in model_id:
            p_id, raw_mid = parse_model_ref(model_id)
            if p_id == "openrouter":
                # OpenRouter expects 'provider/model' (e.g. 'anthropic/claude-3.7-sonnet')
                return raw_mid
            return raw_mid
        return model_id

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
        # Ensure client is an AsyncOpenAI instance (or test mock)
        if client is not None and (isinstance(client, openai.AsyncOpenAI) or hasattr(client, "chat")):
            sdk_client = client
        else:
            api_key = getattr(model.provider, "api_key", None) or "no-key"
            base_url = getattr(model.provider, "base_url", None) or "https://api.openai.com/v1"
            sdk_client = openai.AsyncOpenAI(api_key=api_key, base_url=str(base_url))

        wire_model = self._resolve_wire_model(model.id, provider)

        # Build request parameters
        openai_messages = await _messages_to_openai(messages)
        openai_tools = _tools_to_openai(tools) if tools else None

        stream_params: dict[str, Any] = {}
        if params is not None:
            _apply_common_openai_params(
                stream_params,
                params,
                provider=provider,
                responses=False,
            )

        api_kwargs: dict[str, Any] = dict(stream_params)
        api_kwargs.update(
            {
                "model": wire_model,
                "messages": openai_messages,
                "stream": True,
                "stream_options": {"include_usage": True},
            }
        )

        if openai_tools:
            api_kwargs["tools"] = openai_tools

        if output_type is not None:
            api_kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": output_type.__name__,
                    "schema": pydantic.TypeAdapter(output_type).json_schema(),
                    "strict": True,
                },
            }

        try:
            sdk_stream = await sdk_client.chat.completions.create(**api_kwargs)
        except Exception as exc:
            raise RuntimeError(f"OpenAI driver error for model '{model.id}': {exc}") from exc

        text_started = False
        reasoning_started = False
        tc_state: dict[int, dict[str, Any]] = {}
        usage: types.usage.Usage | None = None
        finish_reason: str | None = None
        response_id: str | None = None
        response_model: str | None = model.id

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
                    reasoning_tokens: int | None = None
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

                # 1. Reasoning delta extraction (DeepSeek R1, o1, thinking)
                reasoning_chunk = (
                    getattr(delta, "reasoning_content", None)
                    or getattr(delta, "reasoning", None)
                    or getattr(delta, "thinking", None)
                )
                if not reasoning_chunk and hasattr(delta, "model_extra") and delta.model_extra:
                    reasoning_chunk = (
                        delta.model_extra.get("reasoning_content")
                        or delta.model_extra.get("reasoning")
                    )

                if reasoning_chunk:
                    if not reasoning_started:
                        reasoning_started = True
                        yield types.events.ReasoningStart(block_id="reasoning")
                    yield types.events.ReasoningDelta(
                        chunk=reasoning_chunk, block_id="reasoning"
                    )

                # 2. Standard text delta extraction
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

                # 3. Tool call deltas
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

                # 4. Finish reason handling
                fn_reason = getattr(choice, "finish_reason", None)
                if fn_reason is not None:
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

            # Cleanup open blocks if stream closed without finish_reason
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
