"""Privacy-safe append-only tool audit log."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from qgis.core import QgsApplication

from geoutility_copilot.core.tools.base import Risk, ToolResult


class AuditLogger:
    """Write one bounded JSON object per executed tool call."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or (
            Path(QgsApplication.qgisSettingsDirPath()) / "geoutility_copilot" / "audit.jsonl"
        )

    def record(
        self,
        turn_id: str,
        tool: str,
        argument_names: list[str],
        risk: Risk,
        result: ToolResult,
        duration_ms: int,
        approval: str = "automatic",
    ) -> None:
        """Append metadata without prompts, arguments, or result data."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "turn_id": turn_id,
            "tool": tool,
            "argument_names": sorted(argument_names),
            "risk": risk.value,
            "approval": approval,
            "ok": result.ok,
            "summary": result.summary,
            "duration_ms": max(0, duration_ms),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, separators=(",", ":"), sort_keys=True) + "\n")
