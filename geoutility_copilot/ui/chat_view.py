"""Role-aware chat message rendering."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Optional

from qgis.PyQt.QtCore import QCoreApplication, Qt, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

MESSAGE_ROLES = frozenset({"user", "assistant", "tool", "error"})


@dataclass(frozen=True)
class RenderedMessage:
    """Inspectable message metadata retained by the view."""

    role: str
    text: str


class ChatView(QScrollArea):
    """Scrollable list of user, assistant, tool, and error messages."""

    undoRequested = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Create the scrollable message container.

        Args:
            parent: Owning Qt widget.
        """
        super().__init__(parent)
        self.setObjectName("GeoUtilityChatView")
        self.setAccessibleName(self.tr("Conversation"))
        self.setWidgetResizable(True)
        self._container = QWidget(self)
        self._layout = QVBoxLayout(self._container)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setWidget(self._container)
        self._messages: list[RenderedMessage] = []

    @property
    def messages(self) -> tuple[RenderedMessage, ...]:
        """Return immutable metadata for rendered messages."""
        return tuple(self._messages)

    def add_message(self, role: str, text: str) -> None:
        """Render one message using its role-specific presentation.

        Args:
            role: One of user, assistant, tool, or error.
            text: Message content to display.
        """
        if role not in MESSAGE_ROLES:
            raise ValueError(f"Unknown chat message role: {role}")
        widget = self._tool_message(text) if role == "tool" else self._text_message(role, text)
        self._layout.addWidget(widget)
        self._messages.append(RenderedMessage(role=role, text=text))
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def clear_messages(self) -> None:
        """Remove all rendered messages."""
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._messages.clear()

    def add_tool_step(self, text: str, undo_token: str) -> None:
        """Render a tool step with a one-shot selection undo action."""
        widget = self._tool_message(text, undo_token)
        self._layout.addWidget(widget)
        self._messages.append(RenderedMessage(role="tool", text=text))

    def _text_message(self, role: str, text: str) -> QTextBrowser:
        browser = QTextBrowser(self._container)
        browser.setObjectName(f"GeoUtilityMessage-{role}")
        browser.setAccessibleName(self.tr("{0} message").format(role.capitalize()))
        browser.setOpenExternalLinks(False)
        browser.setFrameShape(QFrame.Shape.StyledPanel)
        browser.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        if role == "assistant":
            browser.setMarkdown(escape(text))
        else:
            browser.setPlainText(text)
        return browser

    def _tool_message(self, text: str, undo_token: str = "") -> QWidget:
        container = QWidget(self._container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        toggle = QToolButton(container)
        toggle.setObjectName("GeoUtilityMessage-tool")
        toggle.setText(self.tr("Tool step"))
        toggle.setCheckable(True)
        toggle.setArrowType(Qt.ArrowType.RightArrow)
        detail = QLabel(text, container)
        detail.setWordWrap(True)
        detail.hide()

        def set_expanded(expanded: bool) -> None:
            toggle.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
            detail.setVisible(expanded)

        toggle.toggled.connect(set_expanded)
        layout.addWidget(toggle)
        layout.addWidget(detail)
        if undo_token:
            undo = QToolButton(container)
            undo.setText(self.tr("Undo selection"))

            def request_undo() -> None:
                undo.setEnabled(False)
                self.undoRequested.emit(undo_token)

            undo.clicked.connect(request_undo)
            layout.addWidget(undo)
        return container

    def tr(self, message: str) -> str:
        """Translate a user-visible chat string.

        Args:
            message: Source text in English.
        """
        return QCoreApplication.translate("ChatView", message)
