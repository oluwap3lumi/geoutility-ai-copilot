"""Provider-neutral agent-loop tests with no network."""

from __future__ import annotations

from typing import Any

from geoutility_copilot.core.agent import AgentLoop
from geoutility_copilot.core.llm.base import CancelToken, LLMReply, ToolCall
from geoutility_copilot.core.llm.fake import FakeProvider


def test_plain_answer() -> None:
    provider = FakeProvider([LLMReply(text="Hello")])
    result = AgentLoop(provider, _tool_executor).run_turn("system", [], [])

    assert result.text == "Hello"
    assert result.iterations == 1


def test_one_tool_call_and_chained_tool_calls() -> None:
    provider = FakeProvider(
        [
            LLMReply(tool_calls=(ToolCall("1", "first", {"value": 1}),)),
            LLMReply(tool_calls=(ToolCall("2", "second", {"value": 2}),)),
            LLMReply(text="Done"),
        ]
    )
    result = AgentLoop(provider, _tool_executor).run_turn("system", [], [])

    assert result.text == "Done"
    assert result.iterations == 3
    assert len(provider.requests) == 3
    assert provider.requests[1]["messages"][-1]["content"][0]["tool_use_id"] == "1"


def test_tool_error_is_returned_for_recovery() -> None:
    provider = FakeProvider(
        [LLMReply(tool_calls=(ToolCall("1", "fail", {}),)), LLMReply(text="Recovered")]
    )
    result = AgentLoop(provider, _tool_executor).run_turn("system", [], [])

    tool_result = provider.requests[1]["messages"][-1]["content"][0]
    assert result.text == "Recovered"
    assert tool_result["is_error"] is True


def test_iteration_cap() -> None:
    replies = [LLMReply(tool_calls=(ToolCall(str(i), "first", {}),)) for i in range(3)]
    result = AgentLoop(FakeProvider(replies), _tool_executor, max_iterations=3).run_turn(
        "system", [], []
    )

    assert "iteration limit" in result.text


def test_cancel_before_request() -> None:
    token = CancelToken()
    token.cancel()
    result = AgentLoop(FakeProvider([]), _tool_executor).run_turn(
        "system", [], [], cancel_token=token
    )

    assert result.cancelled is True


def _tool_executor(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "fail":
        raise ValueError("synthetic failure")
    return {"name": name, "arguments": arguments}
