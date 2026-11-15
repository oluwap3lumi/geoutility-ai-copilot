"""GeoUtility AI Copilot QGIS plugin package."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qgis.gui import QgisInterface

    from geoutility_copilot.plugin import GeoUtilityCopilotPlugin


def classFactory(iface: QgisInterface) -> GeoUtilityCopilotPlugin:
    """Return the plugin instance created by QGIS.

    Args:
        iface: QGIS application interface supplied by the plugin loader.
    """
    from geoutility_copilot.plugin import GeoUtilityCopilotPlugin

    return GeoUtilityCopilotPlugin(iface)
