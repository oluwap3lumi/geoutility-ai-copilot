"""QGIS plugin lifecycle and dock registration."""

from __future__ import annotations

from typing import Optional

from qgis.core import QgsSettings
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.PyQt.QtWidgets import QAction

from geoutility_copilot.ui.dock import CopilotDock

MENU_NAME = "&GeoUtility AI Copilot"
DOCK_OBJECT_NAME = "GeoUtilityCopilotDock"
VISIBILITY_SETTING = "GeoUtilityCopilot/dockVisible"
GEOMETRY_SETTING = "GeoUtilityCopilot/dockGeometry"


class GeoUtilityCopilotPlugin:
    """Own the QGIS action and dock for one plugin lifecycle."""

    def __init__(self, iface: QgisInterface) -> None:
        """Store the QGIS application interface.

        Args:
            iface: QGIS application interface supplied by the plugin loader.
        """
        self._iface = iface
        self._action: Optional[QAction] = None
        self._dock: Optional[CopilotDock] = None

    @property
    def action(self) -> Optional[QAction]:
        """Return the registered toggle action, if initialized."""
        return self._action

    @property
    def dock(self) -> Optional[CopilotDock]:
        """Return the plugin dock, if initialized."""
        return self._dock

    def initGui(self) -> None:
        """Register the toolbar/menu action and placeholder dock."""
        if self._action is not None:
            return

        settings = QgsSettings()
        should_show = settings.value(VISIBILITY_SETTING, False, type=bool)
        main_window = self._iface.mainWindow()
        action = QAction(self.tr("GeoUtility AI Copilot"), main_window)
        action.setObjectName("GeoUtilityCopilotAction")
        action.setCheckable(True)
        action.setToolTip(self.tr("Open GeoUtility AI Copilot"))
        action.toggled.connect(self._set_dock_visible)

        dock = CopilotDock(main_window)
        dock.setObjectName(DOCK_OBJECT_NAME)
        dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        dock.visibilityChanged.connect(self._sync_action_state)

        self._action = action
        self._dock = dock
        self._iface.addToolBarIcon(action)
        self._iface.addPluginToMenu(MENU_NAME, action)
        self._iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        geometry = settings.value(GEOMETRY_SETTING)
        if geometry is not None:
            dock.restoreGeometry(geometry)
        action.setChecked(should_show)
        dock.setVisible(should_show)

    def unload(self) -> None:
        """Disconnect and remove every plugin-owned QGIS widget."""
        action = self._action
        dock = self._dock
        self._action = None
        self._dock = None

        if action is not None:
            action.toggled.disconnect(self._set_dock_visible)
            self._iface.removePluginMenu(MENU_NAME, action)
            self._iface.removeToolBarIcon(action)
            action.deleteLater()

        if dock is not None:
            QgsSettings().setValue(GEOMETRY_SETTING, dock.saveGeometry())
            dock.shutdown()
            dock.visibilityChanged.disconnect(self._sync_action_state)
            self._iface.removeDockWidget(dock)
            dock.deleteLater()

    def tr(self, message: str) -> str:
        """Translate a user-visible plugin string.

        Args:
            message: Source text in English.
        """
        return QCoreApplication.translate("GeoUtilityCopilotPlugin", message)

    def _set_dock_visible(self, visible: bool) -> None:
        QgsSettings().setValue(VISIBILITY_SETTING, visible)
        if self._dock is not None:
            self._dock.setVisible(visible)

    def _sync_action_state(self, visible: bool) -> None:
        QgsSettings().setValue(VISIBILITY_SETTING, visible)
        if self._action is not None and self._action.isChecked() != visible:
            self._action.setChecked(visible)
