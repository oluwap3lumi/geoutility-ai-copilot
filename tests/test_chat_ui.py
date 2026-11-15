"""QGIS chat-shell tests."""

from __future__ import annotations

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtTest import QTest
from qgis.PyQt.QtWidgets import QToolButton

from geoutility_copilot.ui.chat_view import ChatView
from geoutility_copilot.ui.dock import CopilotDock
from geoutility_copilot.ui.input_bar import InputBar


def test_chat_view_renders_every_role(qgis_app: object) -> None:
    view = ChatView()
    try:
        for role in ("user", "assistant", "tool", "error"):
            view.add_message(role, f"message from {role}")

        assert [message.role for message in view.messages] == [
            "user",
            "assistant",
            "tool",
            "error",
        ]
    finally:
        view.deleteLater()


def test_input_enter_submits_and_shift_enter_adds_newline(qgis_app: object) -> None:
    input_bar = InputBar()
    try:
        submitted: list[str] = []
        input_bar.promptSubmitted.connect(submitted.append)
        input_bar.editor.setText("hello")

        QTest.keyClick(input_bar.editor, Qt.Key.Key_Return, Qt.KeyboardModifier.ShiftModifier)
        assert "\n" in input_bar.editor.toPlainText()

        QTest.keyClick(input_bar.editor, Qt.Key.Key_Return)
        assert submitted == ["hello"]
    finally:
        input_bar.deleteLater()


def test_busy_state_and_clear_are_non_blocking(qgis_app: object) -> None:
    dock = CopilotDock()
    try:
        dock.chat_view.add_message("user", "first")
        dock.input_bar.set_busy(True)
        assert not dock.input_bar.stop_button.isHidden()

        dock.input_bar.set_busy(False)
        assert dock.input_bar.stop_button.isHidden()

        dock.clear()
        assert dock.chat_view.messages == ()
    finally:
        dock.deleteLater()


def test_tool_step_emits_one_shot_undo_token(qgis_app: object) -> None:
    view = ChatView()
    try:
        tokens: list[str] = []
        view.undoRequested.connect(tokens.append)
        view.add_tool_step("Selected 2 features.", "undo-token")
        button = next(
            item for item in view.findChildren(QToolButton) if item.text() == "Undo selection"
        )

        button.click()
        button.click()

        assert tokens == ["undo-token"]
        assert not button.isEnabled()
    finally:
        view.deleteLater()
