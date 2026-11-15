"""Claude wire-format tests using a fake transport."""

from __future__ import annotations

import json

import pytest

from geoutility_copilot.core.llm.base import CancelToken, ProviderError
from geoutility_copilot.core.llm.claude import ClaudeProvider, HttpResponse


class FakeTransport:
    def __init__(self, response: HttpResponse) -> None:
        self.response = response
        self.body = b""
        self.headers: dict[str, str] = {}

    def post(
        self, url: str, headers: dict[str, str], body: bytes, cancel_token: CancelToken
    ) -> HttpResponse:
        self.body = body
        self.headers = headers
        return self.response


def test_text_and_tool_use_mapping() -> None:
    transport = FakeTransport(
        HttpResponse(
            200,
            json.dumps(
                {
                    "content": [
                        {"type": "text", "text": "Checking."},
                        {"type": "tool_use", "id": "tool-1", "name": "inspect", "input": {}},
                    ],
                    "stop_reason": "tool_use",
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                }
            ).encode(),
            "request-1",
        )
    )
    provider = ClaudeProvider("secret", "configured-model", transport)

    reply = provider.complete("system", [], [], CancelToken())
    payload = json.loads(transport.body)

    assert reply.text == "Checking."
    assert reply.tool_calls[0].name == "inspect"
    assert reply.request_id == "request-1"
    assert payload["model"] == "configured-model"
    assert transport.headers["x-api-key"] == "secret"


def test_tool_result_content_is_serialized() -> None:
    transport = FakeTransport(HttpResponse(200, b'{"content":[],"stop_reason":"end_turn"}'))
    provider = ClaudeProvider("secret", "model", transport)
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "1",
                    "content": {"ok": True, "count": 2},
                    "is_error": False,
                }
            ],
        }
    ]

    provider.complete("system", messages, [], CancelToken())

    content = json.loads(transport.body)["messages"][0]["content"][0]["content"]
    assert json.loads(content) == {"ok": True, "count": 2}


def test_unauthorized_error_does_not_expose_key() -> None:
    provider = ClaudeProvider("top-secret", "model", FakeTransport(HttpResponse(401, b"{}")))

    with pytest.raises(ProviderError) as error:
        provider.complete("system", [], [], CancelToken())

    assert "top-secret" not in str(error.value)
