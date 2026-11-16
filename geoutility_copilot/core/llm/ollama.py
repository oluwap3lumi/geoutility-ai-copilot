"""Ollama chat/tool adapter using the shared QGIS HTTP transport."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

from geoutility_copilot.core.llm.base import CancelToken, LLMReply, ProviderError, ToolCall
from geoutility_copilot.core.llm.claude import HttpTransport, post_with_retries


class OllamaProvider:
    """Translate neutral messages to and from Ollama `/api/chat`."""

    def __init__(
        self,
        host: str,
        model: str,
        transport: HttpTransport,
        retry_delays: tuple[float, ...] = (0.5, 1.0),
    ) -> None:
        """Configure a local Ollama endpoint and tool-capable model."""
        parsed = urlparse(host)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ProviderError("Ollama host must be an http(s) URL.")
        self._url = host.rstrip("/") + "/api/chat"
        self._model = model
        self._transport = transport
        self._retry_delays = retry_delays

    def complete(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        cancel_token: CancelToken,
    ) -> LLMReply:
        """Request one non-streaming Ollama response."""
        payload = {
            "model": self._model,
            "messages": [{"role": "system", "content": system}, *_wire_messages(messages)],
            "tools": [_wire_tool(tool) for tool in tools],
            "stream": False,
        }
        response = post_with_retries(
            self._transport,
            self._url,
            {"content-type": "application/json"},
            json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            cancel_token,
            self._retry_delays,
        )
        if response.status >= 400:
            detail = _error_detail(response.body)
            if "support tools" in detail.casefold() or "tool" in detail.casefold():
                raise ProviderError("The selected Ollama model does not support tool calling.")
            raise ProviderError(f"Ollama request failed with HTTP {response.status}: {detail}")
        try:
            data = json.loads(response.body.decode("utf-8"))
            message = data["message"]
        except (KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderError("Ollama returned an invalid response.") from exc
        calls = []
        for index, item in enumerate(message.get("tool_calls", []), start=1):
            function = item.get("function", {})
            arguments = function.get("arguments", {})
            if not isinstance(arguments, dict):
                raise ProviderError("Ollama returned invalid tool arguments.")
            calls.append(ToolCall(f"ollama-{index}", str(function.get("name", "")), arguments))
        return LLMReply(
            text=str(message.get("content", "")),
            tool_calls=tuple(calls),
            stop_reason="tool_use" if calls else "end_turn",
            usage={
                "input_tokens": int(data.get("prompt_eval_count", 0)),
                "output_tokens": int(data.get("eval_count", 0)),
            },
        )


def _wire_tool(tool: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["input_schema"],
        },
    }


def _wire_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    tool_names: dict[str, str] = {}
    for message in messages:
        content = message.get("content", "")
        if not isinstance(content, list):
            output.append({"role": message["role"], "content": str(content)})
            continue
        if message["role"] == "assistant":
            text = "".join(
                str(item.get("text", "")) for item in content if item.get("type") == "text"
            )
            calls = []
            for item in content:
                if item.get("type") != "tool_use":
                    continue
                tool_names[str(item.get("id", ""))] = str(item.get("name", ""))
                calls.append(
                    {
                        "type": "function",
                        "function": {
                            "name": item.get("name", ""),
                            "arguments": item.get("input", {}),
                        },
                    }
                )
            output.append({"role": "assistant", "content": text, "tool_calls": calls})
            continue
        for item in content:
            if item.get("type") == "tool_result":
                call_id = str(item.get("tool_use_id", ""))
                output.append(
                    {
                        "role": "tool",
                        "tool_name": tool_names.get(call_id, "unknown"),
                        "content": json.dumps(item.get("content", {}), separators=(",", ":")),
                    }
                )
    return output


def _error_detail(body: bytes) -> str:
    try:
        data = json.loads(body.decode("utf-8"))
        return str(data.get("error", "request failed"))
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
        return "request failed"
