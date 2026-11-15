"""Registered GIS tools."""

from geoutility_copilot.core.tools.find_unconnected import FindUnconnectedTool
from geoutility_copilot.core.tools.inspect_layers import InspectLayersTool
from geoutility_copilot.core.tools.query_features import QueryFeaturesTool
from geoutility_copilot.core.tools.registry import ToolRegistry
from geoutility_copilot.core.tools.spatial_select import SpatialSelectTool


def create_m1_registry() -> ToolRegistry:
    """Return the fixed Milestone 1 tool registry."""
    return ToolRegistry([InspectLayersTool(), QueryFeaturesTool()])


def create_m2_registry() -> ToolRegistry:
    """Return the available Milestone 2 tool registry."""
    return ToolRegistry(
        [InspectLayersTool(), QueryFeaturesTool(), SpatialSelectTool(), FindUnconnectedTool()]
    )
