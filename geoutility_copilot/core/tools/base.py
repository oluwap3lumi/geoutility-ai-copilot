"""Contracts shared by every registered GIS tool."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from qgis.core import QgsProject


class Risk(str, Enum):
    """Tool safety tier enforced outside model prompts."""

    READ = "read"
    SELECTION = "selection"
    OUTPUT = "output"
    MODIFY = "modify"


@dataclass(frozen=True)
class ToolResult:
    """Small structured result returned to the model."""

    ok: bool
    summary: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""


@dataclass(frozen=True)
class ToolContext:
    """Main-thread QGIS dependencies available to tools."""

    project: QgsProject
    never_send_samples: bool = True
    max_samples: int = 3
    max_result_ids: int = 20
    metric_crs: str = "EPSG:32631"
    model: str = "unknown"


class Tool(Protocol):
    """Interface implemented by fixed, auditable GIS operations."""

    name: str
    description: str
    input_schema: dict[str, Any]
    risk: Risk

    def run(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        """Execute on the QGIS main thread."""
        ...

    def preview(self, args: dict[str, Any], context: ToolContext) -> str:
        """Describe the operation for future approval UI."""
        ...
