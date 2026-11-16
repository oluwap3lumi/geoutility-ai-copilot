"""QGIS chat-shell tests."""

from __future__ import annotations

from inspect import signature
from pathlib import Path

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtTest import QTest
from qgis.PyQt.QtWidgets import QApplication, QTextBrowser, QToolButton

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


def test_tool_step_optional_handle_has_no_secret_like_string_default() -> None:
    parameter = signature(ChatView._tool_message).parameters["undo_handle"]

    assert parameter.default is None


def test_assistant_markdown_escapes_embedded_html(qgis_app: object) -> None:
    view = ChatView()
    try:
        view.add_message("assistant", "**Safe** <img src=x onerror=alert(1)>")
        browser = view.findChild(QTextBrowser)

        assert browser is not None
        assert "<img src=x" not in browser.toHtml()
        assert "&lt;img" in browser.toHtml()
        assert "Safe" in browser.toPlainText()
        assert "<img" in browser.toPlainText()
    finally:
        view.deleteLater()


def test_assistant_copy_button_uses_plain_source_text(qgis_app: object) -> None:
    view = ChatView()
    try:
        view.add_message("assistant", "**Result:** 3 orphans")
        button = next(item for item in view.findChildren(QToolButton) if item.text() == "Copy")

        button.click()

        assert QApplication.clipboard().text() == "**Result:** 3 orphans"
    finally:
        view.deleteLater()


def test_examples_and_plain_text_export(qgis_app: object, tmp_path: Path) -> None:
    dock = CopilotDock()
    try:
        dock.example_buttons[0].click()
        assert dock.input_bar.editor.toPlainText() == "Find transformers without customers"
        dock.chat_view.add_message("user", "hello")
        dock.chat_view.add_message("assistant", "hi")
        destination = tmp_path / "chat.txt"

        dock.export_chat_to(destination)

        assert destination.read_text(encoding="utf-8") == "[USER]\nhello\n\n[ASSISTANT]\nhi\n"
    finally:
        dock.deleteLater()
