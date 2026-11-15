"""Settings and secret-boundary tests."""

from __future__ import annotations

from typing import Any

from qgis.core import QgsSettings

from geoutility_copilot.core.settings import CopilotSettings, load_settings, save_settings
from geoutility_copilot.ui.settings_dialog import SettingsDialog


class MemorySettings:
    """Small QgsSettings-compatible store for core tests."""

    def __init__(self) -> None:
        self.values: dict[str, Any] = {}

    def value(self, key: str, default: Any, type: type) -> Any:
        return type(self.values.get(key, default))

    def setValue(self, key: str, value: Any) -> None:
        self.values[key] = value


class FakeSecretStore:
    """In-memory secret store for dialog tests."""

    def __init__(self) -> None:
        self.api_key = ""

    def has_api_key(self) -> bool:
        return bool(self.api_key)

    def get_api_key(self) -> str:
        return self.api_key

    def set_api_key(self, api_key: str) -> None:
        self.api_key = api_key


def test_settings_round_trip() -> None:
    store = MemorySettings()
    expected = CopilotSettings(
        model="test-model",
        never_send_samples=False,
        metric_crs="EPSG:26331",
        privacy_notice_seen=True,
    )

    save_settings(expected, store)

    assert load_settings(store) == expected


def test_dialog_saves_key_outside_qgssettings(qgis_app: object) -> None:
    QgsSettings().remove("GeoUtilityCopilot")
    secrets = FakeSecretStore()
    dialog = SettingsDialog(secret_store=secrets)
    try:
        dialog.api_key_edit.setText("test-secret-key")
        dialog.model_edit.setText("test-model")
        dialog.schema_map_edit.setPlainText('{"roles":{}}')
        dialog.save()

        assert secrets.api_key == "test-secret-key"
        assert load_settings().model == "test-model"
        values = [str(QgsSettings().value(key)) for key in QgsSettings().allKeys()]
        assert "test-secret-key" not in values
    finally:
        dialog.deleteLater()
        QgsSettings().remove("GeoUtilityCopilot")


def test_dialog_masks_api_key(qgis_app: object) -> None:
    dialog = SettingsDialog(secret_store=FakeSecretStore())
    try:
        assert dialog.api_key_edit.echoMode() == dialog.api_key_edit.EchoMode.Password
    finally:
        dialog.deleteLater()


def test_first_run_privacy_notice_can_be_dismissed(qgis_app: object) -> None:
    from geoutility_copilot.ui.dock import CopilotDock

    QgsSettings().remove("GeoUtilityCopilot")
    dock = CopilotDock()
    try:
        assert not dock.privacy_notice.isHidden()

        dock.dismiss_privacy_notice()

        assert dock.privacy_notice.isHidden()
        assert load_settings().privacy_notice_seen
    finally:
        dock.deleteLater()
        QgsSettings().remove("GeoUtilityCopilot")
