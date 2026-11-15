"""Copilot dock widget and temporary echo flow."""

from __future__ import annotations

from typing import Optional

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QDialog, QDockWidget, QLabel, QPushButton, QVBoxLayout, QWidget

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
        self.clear_button = QPushButton(self.tr("Clear chat"), content)
        self.clear_button.setAccessibleName(self.tr("Clear conversation"))
        self.settings_button = QPushButton(self.tr("Settings"), content)
        self.settings_button.setAccessibleName(self.tr("Open copilot settings"))
        layout.addWidget(self.privacy_notice)
        layout.addWidget(self.chat_view, 1)
        layout.addWidget(self.input_bar)
        layout.addWidget(self.clear_button)
        layout.addWidget(self.settings_button)
        self.setWidget(content)
        self.privacy_notice.setVisible(not load_settings().privacy_notice_seen)

        self.clear_button.clicked.connect(self.clear)
        self.settings_button.clicked.connect(self.open_settings)

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

    def tr(self, message: str) -> str:
        """Translate a user-visible dock string.

        Args:
            message: Source text in English.
        """
        return QCoreApplication.translate("CopilotDock", message)
