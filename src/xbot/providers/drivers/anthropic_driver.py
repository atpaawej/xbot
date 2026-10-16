"""Anthropic wire protocol driver using raw anthropic.AsyncAnthropic."""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Sequence

import anthropic
import pydantic
from ai import types
from ai.models import InferenceRequestParams, Model
from ai.providers.anthropic.protocol import (
    _FINISH_REASONS,
    _apply_anthropic_params,
    _coerce_params,
    _custom_tools_to_anthropic,
    _messages_to_anthropic,
)

from xbot.providers.drivers.base import BaseDriver
from xbot.providers.models import parse_model_ref


class AnthropicDriver(BaseDriver):
    """Driver executing completions against Anthropic's Messages API (/v1/messages)."""

    def _resolve_wire_model(self, model_id: str, provider: str) -> str:
        """Resolve the raw model string expected by Anthropic."""
        if "/" in model_id:
            _, raw_mid = parse_model_ref(model_id)
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
        # Ensure client is an AsyncAnthropic instance (or test mock)
        if client is not None and (isinstance(client, anthropic.AsyncAnthropic) or hasattr(client, "messages")):
            sdk_client = client
        else:
            api_key = getattr(model.provider, "api_key", None) or "no-key"
            base_url = getattr(model.provider, "base_url", None)
            sdk_client = anthropic.AsyncAnthropic(
                api_key=api_key,
                base_url=str(base_url) if base_url else None,
            )

        wire_model = self._resolve_wire_model(model.id, provider)

        system_prompt, anthropic_messages = await _messages_to_anthropic(messages)
        wire_tools = _custom_tools_to_anthropic(tools) if tools else []

        stream_params: dict[str, Any] = {}
        if params is not None:
            _apply_anthropic_params(stream_params, params, provider=provider)

        api_kwargs: dict[str, Any] = dict(stream_params)
        api_kwargs.update(
            {
                "model": wire_model,
                "messages": anthropic_messages,
                "max_tokens": api_kwargs.get("max_tokens", 8192),
            }
        )

        if system_prompt:
            api_kwargs["system"] = system_prompt

        if wire_tools:
            api_kwargs["tools"] = wire_tools

        block_types: dict[int, str] = {}
        tool_ids: dict[int, str] = {}
        tool_names: dict[int, str] = {}
        tool_args_buffer: dict[int, str] = {}
        usage: types.usage.Usage | None = None
        finish_reason: str | None = None
        response_id: str | None = None

        yield types.events.StreamStart()

        try:
            async with sdk_client.messages.stream(**api_kwargs) as sdk_stream:
                async for event in sdk_stream:
                    ev_type = getattr(event, "type", None)

                    if ev_type == "message_start":
                        msg = getattr(event, "message", None)
                        if msg:
                            response_id = getattr(msg, "id", None)
                            u = getattr(msg, "usage", None)
                            if u:
                                usage = types.usage.Usage(
                                    input_tokens=getattr(u, "input_tokens", 0) or 0,
                                    output_tokens=getattr(u, "output_tokens", 0) or 0,
                                )

                    elif ev_type == "content_block_start":
                        block = getattr(event, "content_block", None)
                        idx = getattr(event, "index", 0)
                        b_type = getattr(block, "type", None)
                        block_types[idx] = b_type or "text"

                        if b_type == "text":
                            yield types.events.TextStart(block_id=str(idx))
                        elif b_type == "thinking":
                            yield types.events.ReasoningStart(block_id=str(idx))
                        elif b_type == "tool_use":
                            tid = getattr(block, "id", f"call_{idx}")
                            tname = getattr(block, "name", "")
                            tool_ids[idx] = tid
                            tool_names[idx] = tname
                            tool_args_buffer[idx] = ""
                            yield types.events.ToolStart(
                                tool_call_id=tid,
                                tool_name=tname,
                            )

                    elif ev_type == "content_block_delta":
                        delta = getattr(event, "delta", None)
                        idx = getattr(event, "index", 0)
                        d_type = getattr(delta, "type", None)

                        if d_type == "text_delta":
                            text = getattr(delta, "text", "")
                            if text:
                                yield types.events.TextDelta(
                                    chunk=text,
                                    block_id=str(idx),
                                )
                        elif d_type == "thinking_delta":
                            thinking = getattr(delta, "thinking", "")
                            if thinking:
                                yield types.events.ReasoningDelta(
                                    chunk=thinking,
                                    block_id=str(idx),
                                )
                        elif d_type == "input_json_delta":
                            partial = getattr(delta, "partial_json", "")
                            tool_id = tool_ids.get(idx)
                            if tool_id and partial:
                                tool_args_buffer[idx] = tool_args_buffer.get(idx, "") + partial
                                yield types.events.ToolDelta(
                                    chunk=partial,
                                    tool_call_id=tool_id,
                                )

                    elif ev_type == "content_block_stop":
                        idx = getattr(event, "index", 0)
                        b_type = block_types.get(idx)
                        if b_type == "text":
                            yield types.events.TextEnd(block_id=str(idx))
                        elif b_type == "thinking":
                            yield types.events.ReasoningEnd(block_id=str(idx))
                        elif b_type == "tool_use":
                            tid = tool_ids.get(idx)
                            if tid:
                                call_part = types.messages.ToolCallPart(
                                    tool_call_id=tid,
                                    tool_name=tool_names.get(idx, ""),
                                    tool_args=tool_args_buffer.get(idx, ""),
                                )
                                yield types.events.ToolEnd(
                                    tool_call_id=tid,
                                    tool_call=call_part,
                                )

                    elif ev_type == "message_delta":
                        delta = getattr(event, "delta", None)
                        if delta:
                            raw_stop = getattr(delta, "stop_reason", None)
                            if raw_stop:
                                finish_reason = _FINISH_REASONS.get(raw_stop, "stop")
                        u = getattr(event, "usage", None)
                        if u and usage:
                            usage.output_tokens = getattr(u, "output_tokens", usage.output_tokens)

                yield types.events.StreamEnd(
                    usage=usage,
                    finish_reason=finish_reason or "stop",
                    response_id=response_id,
                    response_model=model.id,
                )
        except Exception as exc:
            raise RuntimeError(f"Anthropic driver error for model '{model.id}': {exc}") from exc
