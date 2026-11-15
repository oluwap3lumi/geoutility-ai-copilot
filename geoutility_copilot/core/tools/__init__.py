"""Registered GIS tools."""

from geoutility_copilot.core.tools.inspect_layers import InspectLayersTool
from geoutility_copilot.core.tools.query_features import QueryFeaturesTool
from geoutility_copilot.core.tools.registry import ToolRegistry


def create_m1_registry() -> ToolRegistry:
    """Return the fixed Milestone 1 tool registry."""
    return ToolRegistry([InspectLayersTool(), QueryFeaturesTool()])
