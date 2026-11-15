"""Explicit approval dialog for output and modify tools."""

from __future__ import annotations

import json
from typing import Optional

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from geoutility_copilot.core.safety import ApprovalRequest, ApprovalResponse
from geoutility_copilot.core.tools.base import Risk


class ApprovalDialog(QDialog):
    """Show exactly what an output or modification will do."""

    def __init__(self, request: ApprovalRequest, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.response = ApprovalResponse(False)
        self.setWindowTitle(self.tr("Approve GeoUtility action"))
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"{request.tool} · {request.risk.value.upper()}", self))
        description = QLabel(request.preview, self)
        description.setWordWrap(True)
        layout.addWidget(description)
        arguments = QPlainTextEdit(json.dumps(request.arguments, indent=2, sort_keys=True), self)
        arguments.setReadOnly(True)
        layout.addWidget(arguments)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel, parent=self)
        approve = QPushButton(self.tr("Approve"), self)
        approve.clicked.connect(lambda: self._finish(True, False))
        buttons.addButton(approve, QDialogButtonBox.ButtonRole.AcceptRole)
        if request.risk is Risk.OUTPUT:
            session = QPushButton(self.tr("Approve for this chat session"), self)
            session.clicked.connect(lambda: self._finish(True, True))
            buttons.addButton(session, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.rejected.connect(lambda: self._finish(False, False))
        layout.addWidget(buttons)

    def _finish(self, approved: bool, session: bool) -> None:
        self.response = ApprovalResponse(approved, session)
        self.accept() if approved else self.reject()

    def tr(self, message: str) -> str:
        return QCoreApplication.translate("ApprovalDialog", message)
