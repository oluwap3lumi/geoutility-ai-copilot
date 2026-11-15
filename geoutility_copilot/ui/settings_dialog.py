"""Provider, privacy, CRS, and API-key settings dialog."""

from __future__ import annotations

from typing import Optional

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from geoutility_copilot.core.secrets import AuthManagerSecretStore, SecretStore, SecretStoreError
from geoutility_copilot.core.settings import CopilotSettings, load_settings, save_settings


class SettingsDialog(QDialog):
    """Edit non-secret preferences and store keys through Auth Manager."""

    def __init__(
        self, parent: Optional[QWidget] = None, secret_store: Optional[SecretStore] = None
    ) -> None:
        """Create and populate the settings dialog.

        Args:
            parent: Owning Qt widget.
            secret_store: Injectable secret store used by tests.
        """
        super().__init__(parent)
        self._secret_store = secret_store or AuthManagerSecretStore()
        self.setWindowTitle(self.tr("GeoUtility AI Copilot Settings"))

        notice = QLabel(
            self.tr(
                "Privacy: layer schema and counts may be sent to the selected provider. "
                "Sample values are disabled by default, and sensitive fields are never sampled."
            ),
            self,
        )
        notice.setWordWrap(True)
        self.provider_combo = QComboBox(self)
        self.provider_combo.addItem("Claude", "claude")
        self.model_edit = QLineEdit(self)
        self.api_key_edit = QLineEdit(self)
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText(self.tr("Leave blank to keep the stored key"))
        self.never_samples_check = QCheckBox(self.tr("Never send sample values"), self)
        self.metric_crs_combo = QComboBox(self)
        self.metric_crs_combo.addItem("UTM zone 31N — EPSG:32631", "EPSG:32631")
        self.metric_crs_combo.addItem("Nigeria West Belt — EPSG:26331", "EPSG:26331")
        self.key_status = QLabel(self)

        form = QFormLayout()
        form.addRow(self.tr("Provider"), self.provider_combo)
        form.addRow(self.tr("Model"), self.model_edit)
        form.addRow(self.tr("Anthropic API key"), self.api_key_edit)
        form.addRow(self.tr("Key status"), self.key_status)
        form.addRow(self.tr("Privacy"), self.never_samples_check)
        form.addRow(self.tr("Metric CRS"), self.metric_crs_combo)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(notice)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self._load()

    def save(self) -> None:
        """Validate and persist the dialog values."""
        model = self.model_edit.text().strip()
        if not model:
            QMessageBox.warning(
                self, self.tr("Invalid settings"), self.tr("Model cannot be empty.")
            )
            return
        api_key = self.api_key_edit.text().strip()
        try:
            if api_key:
                self._secret_store.set_api_key(api_key)
        except SecretStoreError as exc:
            QMessageBox.critical(self, self.tr("API key not saved"), str(exc))
            return
        save_settings(
            CopilotSettings(
                provider=str(self.provider_combo.currentData()),
                model=model,
                never_send_samples=self.never_samples_check.isChecked(),
                metric_crs=str(self.metric_crs_combo.currentData()),
                privacy_notice_seen=True,
            )
        )
        self.accept()

    def _load(self) -> None:
        values = load_settings()
        self._select_data(self.provider_combo, values.provider)
        self.model_edit.setText(values.model)
        self.never_samples_check.setChecked(values.never_send_samples)
        self._select_data(self.metric_crs_combo, values.metric_crs)
        status = self.tr("Stored securely in QGIS Auth Manager")
        if not self._secret_store.has_api_key():
            status = self.tr("No key stored")
        self.key_status.setText(status)

    @staticmethod
    def _select_data(combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def tr(self, message: str) -> str:
        """Translate a user-visible settings string.

        Args:
            message: Source text in English.
        """
        return QCoreApplication.translate("SettingsDialog", message)
