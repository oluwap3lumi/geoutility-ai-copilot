"""Claude Messages API adapter using QGIS networking."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Protocol

from qgis.core import QgsBlockingNetworkRequest, QgsFeedback
from qgis.PyQt.QtCore import QByteArray, QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest

from geoutility_copilot.core.llm.base import (
    CancelledError,
    CancelToken,
    LLMReply,
    ProviderError,
    ToolCall,
)

MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


@dataclass(frozen=True)
class HttpResponse:
    """Plain response safe to pass across threads."""

    status: int
    body: bytes
    request_id: str = ""


class HttpTransport(Protocol):
    """Injectable HTTP boundary."""

    def post(
        self, url: str, headers: dict[str, str], body: bytes, cancel_token: CancelToken
    ) -> HttpResponse:
        """POST bytes and return a plain response."""
        ...


class QgisHttpTransport:
    """Thread-safe blocking transport honoring QGIS proxy and SSL settings."""

    def post(
        self, url: str, headers: dict[str, str], body: bytes, cancel_token: CancelToken
    ) -> HttpResponse:
        """POST through QgsBlockingNetworkRequest.

        Args:
            url: HTTPS endpoint.
            headers: Request headers, including authentication.
            body: JSON request bytes.
            cancel_token: Cooperative cancellation token.
        """
        if cancel_token.is_cancelled():
            raise CancelledError("Request cancelled.")
        request = QNetworkRequest(QUrl(url))
        request.setTransferTimeout(60_000)
        for name, value in headers.items():
            request.setRawHeader(
                QByteArray(name.encode("ascii")), QByteArray(value.encode("utf-8"))
            )
        feedback = QgsFeedback()
        network = QgsBlockingNetworkRequest()
        error = network.post(request, QByteArray(body), False, feedback)
        if cancel_token.is_cancelled():
            feedback.cancel()
            raise CancelledError("Request cancelled.")
        if error != QgsBlockingNetworkRequest.ErrorCode.NoError:
            raise ProviderError(f"Network request failed: {network.errorMessage()}")
        reply = network.reply()
        status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        request_id = bytes(reply.rawHeader(QByteArray(b"request-id"))).decode("utf-8", "replace")
        return HttpResponse(int(status or 0), bytes(reply.content()), request_id)


class ClaudeProvider:
    """Translate neutral messages to and from Claude's Messages API."""

    def __init__(
        self,
        api_key: str,
        model: str,
        transport: HttpTransport,
        max_tokens: int = 2048,
        retry_delays: tuple[float, ...] = (0.5, 1.0),
    ) -> None:
        """Configure the provider.

        Args:
            api_key: Secret used only in the request header.
            model: Configured Claude model identifier.
            transport: HTTP implementation.
            max_tokens: Maximum generated tokens.
        """
        self._api_key = api_key
        self._model = model
        self._transport = transport
        self._max_tokens = max_tokens
        self._retry_delays = retry_delays

    def complete(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        cancel_token: CancelToken,
    ) -> LLMReply:
        """Request and parse one Claude response."""
        payload = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "system": system,
            "messages": [_wire_message(message) for message in messages],
            "tools": tools,
        }
        response = post_with_retries(
            self._transport,
            MESSAGES_URL,
            {
                "x-api-key": self._api_key,
                "anthropic-version": ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
            json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            cancel_token,
            self._retry_delays,
        )
        if response.status == 401:
            raise ProviderError("API key rejected. Check the key in Settings.")
        if response.status >= 400:
            raise ProviderError(f"Claude request failed with HTTP {response.status}.")
        try:
            data = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderError("Claude returned an invalid response.") from exc
        return _parse_reply(data, response.request_id)


def _wire_message(message: dict[str, Any]) -> dict[str, Any]:
    content = message.get("content", "")
    if not isinstance(content, list):
        return {"role": message["role"], "content": content}
    blocks = []
    for block in content:
        converted = dict(block)
        if converted.get("type") == "tool_result" and not isinstance(converted.get("content"), str):
            converted["content"] = json.dumps(converted["content"], separators=(",", ":"))
        blocks.append(converted)
    return {"role": message["role"], "content": blocks}


def post_with_retries(
    transport: HttpTransport,
    url: str,
    headers: dict[str, str],
    body: bytes,
    cancel_token: CancelToken,
    retry_delays: tuple[float, ...],
) -> HttpResponse:
    """Retry rate limits and server failures with cancellable bounded delays."""
    for attempt in range(len(retry_delays) + 1):
        response = transport.post(url, headers, body, cancel_token)
        if response.status != 429 and response.status < 500:
            return response
        if attempt == len(retry_delays):
            return response
        deadline = time.monotonic() + retry_delays[attempt]
        while time.monotonic() < deadline:
            if cancel_token.is_cancelled():
                raise CancelledError("Request cancelled.")
            time.sleep(min(0.05, max(0, deadline - time.monotonic())))
    raise ProviderError("Network retry failed.")


def _parse_reply(data: dict[str, Any], request_id: str) -> LLMReply:
    text_parts = []
    tool_calls = []
    for block in data.get("content", []):
        if block.get("type") == "text":
            text_parts.append(str(block.get("text", "")))
        elif block.get("type") == "tool_use":
            tool_calls.append(
                ToolCall(
                    id=str(block.get("id", "")),
                    name=str(block.get("name", "")),
                    arguments=dict(block.get("input", {})),
                )
            )
    usage = data.get("usage", {})
    return LLMReply(
        text="".join(text_parts),
        tool_calls=tuple(tool_calls),
        stop_reason=str(data.get("stop_reason", "end_turn")),
        usage={
            "input_tokens": int(usage.get("input_tokens", 0)),
            "output_tokens": int(usage.get("output_tokens", 0)),
        },
        request_id=request_id,
    )
