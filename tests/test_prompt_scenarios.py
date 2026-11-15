"""Deterministic composite prompt tool-chain tests without network calls."""

from __future__ import annotations

from typing import Any

from geoutility_copilot.core.agent import AgentLoop
from geoutility_copilot.core.llm.base import LLMReply, ToolCall
from geoutility_copilot.core.llm.fake import FakeProvider


def test_overloaded_along_selected_feeder_chains_spatial_and_attribute_filters() -> None:
    provider = FakeProvider(
        [
            LLMReply(tool_calls=(ToolCall("1", "inspect_layers", {"layer": "feeders"}),)),
            LLMReply(
                tool_calls=(
                    ToolCall(
                        "2",
                        "spatial_select",
                        {
                            "target_layer": "transformers",
                            "reference_layer": "feeders",
                            "relationship": "within_distance",
                            "distance_m": 50,
                            "reference_selected_only": True,
                        },
                    ),
                )
            ),
            LLMReply(
                tool_calls=(
                    ToolCall(
                        "3",
                        "query_features",
                        {
                            "layer": "transformers",
                            "expression": '"load_kva" > "rated_kva"',
                            "select": True,
                            "mode": "intersect",
                        },
                    ),
                )
            ),
            LLMReply(text="One overloaded transformer is along the selected feeder."),
        ]
    )
    calls: list[tuple[str, dict[str, Any]]] = []

    result = AgentLoop(provider, lambda name, args: _record(calls, name, args)).run_turn(
        "system", [{"role": "user", "content": "Find overloaded DSS along this feeder"}], []
    )

    assert [name for name, _ in calls] == ["inspect_layers", "spatial_select", "query_features"]
    assert calls[1][1]["reference_selected_only"] is True
    assert calls[2][1]["mode"] == "intersect"
    assert "One overloaded" in result.text


def test_orphan_prompt_uses_count_only_before_offering_output() -> None:
    provider = FakeProvider(
        [
            LLMReply(tool_calls=(ToolCall("1", "inspect_layers", {}),)),
            LLMReply(
                tool_calls=(
                    ToolCall(
                        "2",
                        "find_unconnected",
                        {
                            "asset_layer": "transformers",
                            "related_layer": "customers",
                            "mode": "attribute_key",
                            "asset_key": "transformer_id",
                            "related_key": "transformer_id",
                            "create_layer": False,
                        },
                    ),
                )
            ),
            LLMReply(text="Three transformers are unconnected. I can create a result layer."),
        ]
    )
    calls: list[tuple[str, dict[str, Any]]] = []

    AgentLoop(provider, lambda name, args: _record(calls, name, args)).run_turn(
        "system", [{"role": "user", "content": "Find transformers without customers"}], []
    )

    assert calls[1][0] == "find_unconnected"
    assert calls[1][1]["create_layer"] is False


def test_ambiguous_feeder_asks_back_without_a_tool_call() -> None:
    provider = FakeProvider([LLMReply(text="Please select or name exactly one 11kV feeder.")])
    calls: list[tuple[str, dict[str, Any]]] = []

    result = AgentLoop(provider, lambda name, args: _record(calls, name, args)).run_turn(
        "system", [{"role": "user", "content": "Find overloaded DSS along this feeder"}], []
    )

    assert calls == []
    assert "exactly one" in result.text


def _record(
    calls: list[tuple[str, dict[str, Any]]], name: str, args: dict[str, Any]
) -> dict[str, Any]:
    calls.append((name, args))
    return {"ok": True, "count": 1}
