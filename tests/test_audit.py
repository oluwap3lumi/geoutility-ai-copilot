"""Privacy and append behavior for the local audit log."""

from __future__ import annotations

import json
from pathlib import Path

from geoutility_copilot.core.audit import AuditLogger
from geoutility_copilot.core.tools.base import Risk, ToolResult


def test_audit_appends_metadata_without_raw_values(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    logger = AuditLogger(path)
    secret_value = "sk-ant-do-not-log"
    result = ToolResult(True, "Matched 2 features.", {"raw": secret_value})

    logger.record(
        "turn-1",
        "query_features",
        ["layer", "expression"],
        Risk.SELECTION,
        result,
        12,
    )
    logger.record("turn-2", "inspect_layers", [], Risk.READ, result, 1)

    text = path.read_text(encoding="utf-8")
    entries = [json.loads(line) for line in text.splitlines()]
    assert len(entries) == 2
    assert entries[0]["argument_names"] == ["expression", "layer"]
    assert entries[0]["risk"] == "selection"
    assert secret_value not in text
    assert "raw" not in text
