"""QGIS chat-shell tests."""

from __future__ import annotations

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtTest import QTest

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


def test_echo_stop_and_clear_are_non_blocking(qgis_app: object) -> None:
    dock = CopilotDock()
    try:
        dock.input_bar.editor.setText("first")

        dock.input_bar.submit()
        assert [message.role for message in dock.chat_view.messages] == ["user"]
        assert not dock.input_bar.stop_button.isHidden()

        dock.stop()
        assert [message.role for message in dock.chat_view.messages] == ["user", "error"]
        assert dock.input_bar.stop_button.isHidden()

        dock.clear()
        assert dock.chat_view.messages == ()
    finally:
        dock.deleteLater()


def test_echo_completes_on_timer(qgis_app: object) -> None:
    dock = CopilotDock()
    try:
        dock.input_bar.editor.setText("layers")
        dock.input_bar.submit()

        QTest.qWait(50)

        assert dock.chat_view.messages[-1].role == "assistant"
        assert dock.chat_view.messages[-1].text == "Echo: layers"
    finally:
        dock.deleteLater()
