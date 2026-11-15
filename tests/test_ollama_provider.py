"""Ollama wire-format tests using recorded JSON and no network."""

from __future__ import annotations

import json

import pytest

from geoutility_copilot.core.llm.base import CancelToken, ProviderError
from geoutility_copilot.core.llm.claude import HttpResponse
from geoutility_copilot.core.llm.ollama import OllamaProvider


class FakeTransport:
    def __init__(self, response: HttpResponse) -> None:
        self.response = response
        self.url = ""
        self.body = b""

    def post(
        self, url: str, headers: dict[str, str], body: bytes, cancel_token: CancelToken
    ) -> HttpResponse:
        self.url = url
        self.body = body
        return self.response


def test_plain_reply_and_tool_schema_mapping() -> None:
    transport = FakeTransport(
        HttpResponse(
            200,
            json.dumps(
                {
                    "message": {"role": "assistant", "content": "Hello"},
                    "done": True,
                    "prompt_eval_count": 12,
                    "eval_count": 3,
                }
            ).encode(),
        )
    )
    provider = OllamaProvider("http://localhost:11434", "qwen3", transport)

    reply = provider.complete(
        "system",
        [{"role": "user", "content": "hello"}],
        [
            {
                "name": "inspect_layers",
                "description": "Inspect layers.",
                "input_schema": {"type": "object", "properties": {}},
            }
        ],
        CancelToken(),
    )
    payload = json.loads(transport.body)

    assert transport.url == "http://localhost:11434/api/chat"
    assert payload["stream"] is False
    assert payload["messages"][0] == {"role": "system", "content": "system"}
    assert payload["tools"][0]["function"]["parameters"]["type"] == "object"
    assert reply.text == "Hello"
    assert reply.usage == {"input_tokens": 12, "output_tokens": 3}


def test_tool_call_and_result_history_mapping() -> None:
    transport = FakeTransport(
        HttpResponse(
            200,
            b'{"message":{"role":"assistant","content":"","tool_calls":[{"function":{"name":"inspect_layers","arguments":{}}}]}}',
        )
    )
    provider = OllamaProvider("http://localhost:11434/", "model", transport)
    history = [
        {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": "call-1", "name": "inspect_layers", "input": {}}
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "call-1",
                    "content": {"ok": True, "summary": "Found 2 layers"},
                    "is_error": False,
                }
            ],
        },
    ]

    reply = provider.complete("system", history, [], CancelToken())
    messages = json.loads(transport.body)["messages"]

    assert messages[1]["tool_calls"][0]["function"]["name"] == "inspect_layers"
    assert messages[2]["role"] == "tool"
    assert messages[2]["tool_name"] == "inspect_layers"
    assert json.loads(messages[2]["content"])["ok"] is True
    assert reply.tool_calls[0].name == "inspect_layers"
    assert reply.stop_reason == "tool_use"


def test_unsupported_tool_model_has_clear_error() -> None:
    provider = OllamaProvider(
        "http://localhost:11434",
        "plain-model",
        FakeTransport(HttpResponse(400, b'{"error":"model does not support tools"}')),
    )

    with pytest.raises(ProviderError, match="does not support tool calling"):
        provider.complete("system", [], [], CancelToken())


def test_invalid_host_and_response_are_rejected() -> None:
    with pytest.raises(ProviderError, match="http"):
        OllamaProvider("localhost:11434", "model", FakeTransport(HttpResponse(200, b"{}")))

    provider = OllamaProvider(
        "http://localhost:11434", "model", FakeTransport(HttpResponse(200, b"not-json"))
    )
    with pytest.raises(ProviderError, match="invalid response"):
        provider.complete("system", [], [], CancelToken())
