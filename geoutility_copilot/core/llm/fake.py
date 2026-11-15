"""Scripted provider used by deterministic tests."""

from __future__ import annotations

from typing import Any

from geoutility_copilot.core.llm.base import CancelToken, LLMReply


class FakeProvider:
    """Return scripted replies and record every request."""

    def __init__(self, replies: list[LLMReply]) -> None:
        self._replies = list(replies)
        self.requests: list[dict[str, Any]] = []

    def complete(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        cancel_token: CancelToken,
    ) -> LLMReply:
        """Pop the next scripted response."""
        self.requests.append({"system": system, "messages": list(messages), "tools": tools})
        if not self._replies:
            raise RuntimeError("FakeProvider script exhausted")
        return self._replies.pop(0)
