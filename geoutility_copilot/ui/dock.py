"""Copilot dock widget and temporary echo flow."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from qgis.PyQt.QtCore import QCoreApplication, QUrl
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtWidgets import (
    QDialog,
    QDockWidget,
    QFileDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from geoutility_copilot.core.audit import AuditLogger
from geoutility_copilot.core.settings import load_settings, mark_privacy_notice_seen
from geoutility_copilot.ui.chat_view import ChatView
from geoutility_copilot.ui.input_bar import InputBar
from geoutility_copilot.ui.settings_dialog import SettingsDialog


class CopilotDock(QDockWidget):
    """Compose the chat shell while business logic remains outside UI modules."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Build the chat shell and temporary echo responder.

        Args:
            parent: QGIS main window.
        """
        super().__init__(self.tr("GeoUtility AI Copilot"), parent)
        content = QWidget(self)
        layout = QVBoxLayout(content)
        self.privacy_notice = QWidget(content)
        privacy_layout = QVBoxLayout(self.privacy_notice)
        privacy_label = QLabel(
            self.tr(
                "Privacy: project schema and counts may be sent to the selected AI provider. "
                "Sample values are disabled by default."
            ),
            self.privacy_notice,
        )
        privacy_label.setWordWrap(True)
        dismiss_privacy = QPushButton(self.tr("I understand"), self.privacy_notice)
        dismiss_privacy.clicked.connect(self.dismiss_privacy_notice)
        privacy_layout.addWidget(privacy_label)
        privacy_layout.addWidget(dismiss_privacy)
        self.chat_view = ChatView(content)
        self.input_bar = InputBar(content)
        self.example_buttons = []
        for prompt in (
            self.tr("Find transformers without customers"),
            self.tr("Select poles within 50 m of the selected feeder"),
            self.tr("Generate a network asset validation report"),
        ):
            button = QPushButton(prompt, content)
            button.clicked.connect(lambda checked=False, value=prompt: self._use_example(value))
            self.example_buttons.append(button)
        self.clear_button = QPushButton(self.tr("Clear chat"), content)
        self.clear_button.setAccessibleName(self.tr("Clear conversation"))
        self.settings_button = QPushButton(self.tr("Settings"), content)
        self.settings_button.setAccessibleName(self.tr("Open copilot settings"))
        settings = load_settings()
        self.status_label = QLabel(
            self.tr("{0} · {1}{2}").format(
                settings.provider,
                settings.model,
                self.tr(" · read-only") if settings.read_only else "",
            ),
            content,
        )
        self.new_session_button = QPushButton(self.tr("New session"), content)
        self.export_button = QPushButton(self.tr("Export chat"), content)
        self.audit_button = QPushButton(self.tr("Open audit log"), content)
        layout.addWidget(self.privacy_notice)
        layout.addWidget(self.chat_view, 1)
        for button in self.example_buttons:
            layout.addWidget(button)
        layout.addWidget(self.input_bar)
        layout.addWidget(self.clear_button)
        layout.addWidget(self.new_session_button)
        layout.addWidget(self.settings_button)
        layout.addWidget(self.export_button)
        layout.addWidget(self.audit_button)
        layout.addWidget(self.status_label)
        self.setWidget(content)
        self.privacy_notice.setVisible(not load_settings().privacy_notice_seen)

        self.clear_button.clicked.connect(self.clear)
        self.new_session_button.clicked.connect(self.clear)
        self.settings_button.clicked.connect(self.open_settings)
        self.export_button.clicked.connect(self.export_chat)
        self.audit_button.clicked.connect(self.open_audit_log)

    def clear(self) -> None:
        """Cancel pending echo work and clear the conversation."""
        self.input_bar.set_busy(False)
        self.input_bar.clear()
        self.chat_view.clear_messages()

    def shutdown(self) -> None:
        """Stop pending UI work before plugin unload."""
        self.input_bar.set_busy(False)

    def open_settings(self) -> None:
        """Open the modal settings editor."""
        if SettingsDialog(self).exec() == QDialog.DialogCode.Accepted:
            self.privacy_notice.hide()

    def dismiss_privacy_notice(self) -> None:
        """Persist acknowledgement and hide the first-run notice."""
        mark_privacy_notice_seen()
        self.privacy_notice.hide()

    def prompt_sent(self) -> None:
        """Clear prompt text after the controller accepts it."""
        self.input_bar.clear()

    def set_usage(self, usage: str) -> None:
        """Show the latest provider token hint."""
        self.status_label.setText(
            f"{self.status_label.text().split(' · tokens:')[0]} · tokens: {usage}"
        )

    def export_chat(self) -> None:
        """Export the visible conversation to a user-selected text file."""
        filename, _ = QFileDialog.getSaveFileName(
            self, self.tr("Export chat"), "geoutility-chat.txt", self.tr("Text files (*.txt)")
        )
        if filename:
            self.export_chat_to(Path(filename))

    def export_chat_to(self, path: Path) -> None:
        """Write a plain-text chat export to an explicitly selected path."""
        path.write_text(self.chat_view.export_text(), encoding="utf-8")

    def open_audit_log(self) -> None:
        """Open the profile-local audit log when it exists."""
        path = AuditLogger().path
        if not path.exists():
            self.chat_view.add_message("error", self.tr("No audit log has been created yet."))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _use_example(self, prompt: str) -> None:
        self.input_bar.editor.setPlainText(prompt)
        self.input_bar.editor.setFocus()

    def tr(self, message: str) -> str:
        """Translate a user-visible dock string.

        Args:
            message: Source text in English.
        """
        return QCoreApplication.translate("CopilotDock", message)
