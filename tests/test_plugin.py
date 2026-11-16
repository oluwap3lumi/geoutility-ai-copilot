"""QGIS plugin lifecycle tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from qgis.core import QgsSettings
from qgis.gui import QgisInterface
from qgis.PyQt.QtWidgets import QDockWidget

from geoutility_copilot import classFactory
from geoutility_copilot.plugin import (
    DOCK_OBJECT_NAME,
    GEOMETRY_SETTING,
    VISIBILITY_SETTING,
    GeoUtilityCopilotPlugin,
)


@pytest.fixture
def plugin(qgis_iface: QgisInterface) -> Iterator[GeoUtilityCopilotPlugin]:
    QgsSettings().remove("GeoUtilityCopilot")
    instance = classFactory(qgis_iface)
    yield instance
    instance.unload()
    QgsSettings().remove("GeoUtilityCopilot")


def test_class_factory_creates_plugin(qgis_iface: QgisInterface) -> None:
    instance = classFactory(qgis_iface)

    assert isinstance(instance, GeoUtilityCopilotPlugin)


def test_action_toggles_dock(plugin: GeoUtilityCopilotPlugin) -> None:
    plugin.initGui()

    assert plugin.action is not None
    assert not plugin.action.icon().isNull()
    assert plugin.dock is not None
    assert plugin.dock.objectName() == DOCK_OBJECT_NAME
    assert plugin.dock.isHidden()

    plugin.action.setChecked(True)

    assert not plugin.dock.isHidden()
    plugin.action.setChecked(False)
    assert plugin.dock.isHidden()


def test_unload_removes_dock_and_supports_five_reload_cycles(
    qgis_iface: QgisInterface,
) -> None:
    for _ in range(5):
        plugin = classFactory(qgis_iface)
        plugin.initGui()
        dock = plugin.dock

        assert dock is not None
        plugin.unload()
        qgis_iface.mainWindow().findChildren(QDockWidget)

        assert plugin.action is None
        assert plugin.dock is None
        assert dock.parent() is None or not dock.isVisible()


def test_dock_visibility_and_geometry_are_persisted(plugin: GeoUtilityCopilotPlugin) -> None:
    plugin.initGui()
    assert plugin.action is not None
    assert plugin.dock is not None

    plugin.action.setChecked(True)
    assert QgsSettings().value(VISIBILITY_SETTING, type=bool)
    plugin.unload()

    assert QgsSettings().value(GEOMETRY_SETTING) is not None
