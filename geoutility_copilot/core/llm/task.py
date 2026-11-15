"""QgsTask boundary for provider network calls."""

from __future__ import annotations

from typing import Any, Optional

from qgis.core import QgsTask
from qgis.PyQt.QtCore import QObject, pyqtSignal

from geoutility_copilot.core.llm.base import (
    CancelToken,
    LLMProvider,
    LLMReply,
    ProviderError,
)


class CompletionSignals(QObject):
    """Deliver plain provider results back on the main thread."""

    completed = pyqtSignal(object)
    failed = pyqtSignal(str)


class CompletionTask(QgsTask):
    """Run exactly one provider completion without QGIS layer/widget access."""

    def __init__(
        self,
        provider: LLMProvider,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> None:
        """Copy plain request data for execution on a worker thread.

        Args:
            provider: Configured model provider.
            system: System prompt plus serialized snapshot.
            messages: Plain neutral conversation messages.
            tools: Plain neutral tool specifications.
        """
        super().__init__("GeoUtility AI completion", QgsTask.Flag.CanCancel)
        self.signals = CompletionSignals()
        self._provider = provider
        self._system = system
        self._messages = list(messages)
        self._tools = list(tools)
        self._token = CancelToken()
        self._reply: Optional[LLMReply] = None
        self._error = ""

    def run(self) -> bool:
        """Execute the provider call on the QgsTask worker."""
        try:
            self._reply = self._provider.complete(
                self._system, self._messages, self._tools, self._token
            )
            return not self._token.is_cancelled()
        except ProviderError as exc:
            self._error = str(exc)
            return False

    def cancel(self) -> None:
        """Request cooperative provider cancellation."""
        self._token.cancel()
        super().cancel()

    def finished(self, result: bool) -> None:
        """Emit the plain result after QGIS returns to the main thread.

        Args:
            result: Whether ``run`` completed successfully.
        """
        if result and self._reply is not None:
            self.signals.completed.emit(self._reply)
        elif self._token.is_cancelled():
            self.signals.failed.emit("Request cancelled.")
        else:
            self.signals.failed.emit(self._error or "The model request failed.")
