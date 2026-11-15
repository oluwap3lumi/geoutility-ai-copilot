"""Provider, privacy, CRS, and API-key settings dialog."""

from __future__ import annotations

from typing import Optional

from qgis.core import QgsProject
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
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from geoutility_copilot.core.schema_map import (
    load_schema_map,
    parse_schema_map,
    propose_schema_map,
    save_schema_map,
    validate_schema_map,
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
        ollama_notice = QLabel(
            self.tr("Ollama requires a locally available model that supports tool calling."), self
        )
        ollama_notice.setWordWrap(True)
        self.provider_combo = QComboBox(self)
        self.provider_combo.addItem("Claude", "claude")
        self.provider_combo.addItem("Ollama (local)", "ollama")
        self.model_edit = QLineEdit(self)
        self.api_key_edit = QLineEdit(self)
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText(self.tr("Leave blank to keep the stored key"))
        self.never_samples_check = QCheckBox(self.tr("Never send sample values"), self)
        self.read_only_check = QCheckBox(self.tr("Read-only mode"), self)
        self.metric_crs_combo = QComboBox(self)
        self.metric_crs_combo.addItem("UTM zone 31N — EPSG:32631", "EPSG:32631")
        self.metric_crs_combo.addItem("Nigeria West Belt — EPSG:26331", "EPSG:26331")
        self.key_status = QLabel(self)
        self.ollama_host_edit = QLineEdit(self)
        self.schema_map_edit = QPlainTextEdit(self)
        self.schema_map_edit.setMinimumHeight(180)
        self.propose_schema_button = QPushButton(self.tr("Propose from project"), self)
        self.propose_schema_button.clicked.connect(self._propose_schema_map)

        form = QFormLayout()
        form.addRow(self.tr("Provider"), self.provider_combo)
        form.addRow(self.tr("Model"), self.model_edit)
        form.addRow(self.tr("Anthropic API key"), self.api_key_edit)
        form.addRow(self.tr("Ollama host"), self.ollama_host_edit)
        form.addRow(self.tr("Key status"), self.key_status)
        form.addRow(self.tr("Privacy"), self.never_samples_check)
        form.addRow(self.tr("Safety"), self.read_only_check)
        form.addRow(self.tr("Metric CRS"), self.metric_crs_combo)
        form.addRow(self.tr("Schema map (JSON)"), self.schema_map_edit)
        form.addRow("", self.propose_schema_button)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(notice)
        layout.addWidget(ollama_notice)
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
            schema_map = parse_schema_map(self.schema_map_edit.toPlainText())
        except (TypeError, ValueError) as exc:
            QMessageBox.warning(self, self.tr("Invalid schema map"), str(exc))
            return
        project = QgsProject.instance()
        mapping_errors = validate_schema_map(schema_map, project) if project.mapLayers() else []
        if mapping_errors:
            QMessageBox.warning(self, self.tr("Invalid schema map"), "\n".join(mapping_errors))
            return
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
                read_only=self.read_only_check.isChecked(),
                ollama_host=self.ollama_host_edit.text().strip(),
            )
        )
        save_schema_map(schema_map)
        self.accept()

    def _load(self) -> None:
        values = load_settings()
        self._select_data(self.provider_combo, values.provider)
        self.model_edit.setText(values.model)
        self.never_samples_check.setChecked(values.never_send_samples)
        self.read_only_check.setChecked(values.read_only)
        self.ollama_host_edit.setText(values.ollama_host)
        self._select_data(self.metric_crs_combo, values.metric_crs)
        self.schema_map_edit.setPlainText(load_schema_map().to_json())
        status = self.tr("Stored securely in QGIS Auth Manager")
        if not self._secret_store.has_api_key():
            status = self.tr("No key stored")
        self.key_status.setText(status)

    def _propose_schema_map(self) -> None:
        """Populate an editable proposal without persisting it."""
        mapping = propose_schema_map(
            QgsProject.instance(), str(self.metric_crs_combo.currentData())
        )
        self.schema_map_edit.setPlainText(mapping.to_json())

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
