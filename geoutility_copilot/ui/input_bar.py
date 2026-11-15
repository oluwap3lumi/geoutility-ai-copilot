"""Prompt input controls for the copilot dock."""

from __future__ import annotations

from typing import Optional

from qgis.PyQt.QtCore import QCoreApplication, Qt, pyqtSignal
from qgis.PyQt.QtGui import QKeyEvent
from qgis.PyQt.QtWidgets import QHBoxLayout, QPushButton, QTextEdit, QVBoxLayout, QWidget


class PromptEdit(QTextEdit):
    """Multiline editor that emits submit on unmodified Enter."""

    submitRequested = pyqtSignal()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Submit on Enter and preserve Shift+Enter for newlines.

        Args:
            event: Key event delivered by Qt.
        """
        is_enter = event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
        has_shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        if is_enter and not has_shift:
            self.submitRequested.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class InputBar(QWidget):
    """Prompt editor with Send and Stop controls."""

    promptSubmitted = pyqtSignal(str)
    stopRequested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Create input controls.

        Args:
            parent: Owning Qt widget.
        """
        super().__init__(parent)
        self.editor = PromptEdit(self)
        self.editor.setObjectName("GeoUtilityPromptEdit")
        self.editor.setAccessibleName(self.tr("Message GeoUtility AI Copilot"))
        self.editor.setPlaceholderText(self.tr("Ask about your QGIS project…"))
        self.editor.setMaximumHeight(120)

        self.send_button = QPushButton(self.tr("Send"), self)
        self.send_button.setObjectName("GeoUtilitySendButton")
        self.send_button.setAccessibleName(self.tr("Send message"))
        self.stop_button = QPushButton(self.tr("Stop"), self)
        self.stop_button.setObjectName("GeoUtilityStopButton")
        self.stop_button.setAccessibleName(self.tr("Stop current request"))
        self.stop_button.hide()

        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.send_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.editor)
        layout.addLayout(button_layout)

        self.editor.submitRequested.connect(self.submit)
        self.send_button.clicked.connect(self.submit)
        self.stop_button.clicked.connect(self.stopRequested.emit)

    def submit(self) -> None:
        """Emit the trimmed prompt when it is non-empty."""
        prompt = self.editor.toPlainText().strip()
        if prompt:
            self.promptSubmitted.emit(prompt)

    def clear(self) -> None:
        """Clear the prompt editor."""
        self.editor.clear()

    def set_busy(self, busy: bool) -> None:
        """Switch between send and stop states.

        Args:
            busy: Whether a request is currently active.
        """
        self.editor.setEnabled(not busy)
        self.send_button.setVisible(not busy)
        self.stop_button.setVisible(busy)
        self.stop_button.setEnabled(busy)

    def tr(self, message: str) -> str:
        """Translate a user-visible input string.

        Args:
            message: Source text in English.
        """
        return QCoreApplication.translate("InputBar", message)
