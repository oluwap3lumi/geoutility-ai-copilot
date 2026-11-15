"""Main-thread controller connecting the dock to provider tasks."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Optional, Protocol
from uuid import uuid4

from qgis.core import QgsApplication, QgsProject
from qgis.PyQt.QtCore import QObject, pyqtSignal

from geoutility_copilot.core.audit import AuditLogger
from geoutility_copilot.core.context import build_layer_snapshot
from geoutility_copilot.core.llm.base import LLMProvider, LLMReply
from geoutility_copilot.core.llm.claude import ClaudeProvider, QgisHttpTransport
from geoutility_copilot.core.llm.task import CompletionTask
from geoutility_copilot.core.secrets import AuthManagerSecretStore, SecretStore
from geoutility_copilot.core.settings import load_settings
from geoutility_copilot.core.tools import create_m1_registry
from geoutility_copilot.core.tools.base import ToolContext
from geoutility_copilot.core.tools.registry import ToolRegistry

ProviderFactory = Callable[[str, str], LLMProvider]


class TaskScheduler(Protocol):
    """Scheduling boundary used to make controller tests synchronous."""

    def addTask(self, task: CompletionTask) -> None:
        """Schedule a completion task."""
        ...


class AgentController(QObject):
    """Own conversation state and schedule provider work off-thread."""

    messageReady = pyqtSignal(str, str)
    busyChanged = pyqtSignal(bool)

    def __init__(
        self,
        project: Optional[QgsProject] = None,
        secret_store: Optional[SecretStore] = None,
        provider_factory: Optional[ProviderFactory] = None,
        scheduler: Optional[TaskScheduler] = None,
        registry: Optional[ToolRegistry] = None,
        audit_logger: Optional[AuditLogger] = None,
    ) -> None:
        """Configure the controller dependencies.

        Args:
            project: Live project accessed only when a turn starts on the main thread.
            secret_store: Secure key source.
            provider_factory: Injectable provider construction function.
            scheduler: QgsTask-compatible scheduler.
        """
        super().__init__()
        self._project = project or QgsProject.instance()
        self._secrets = secret_store or AuthManagerSecretStore()
        self._provider_factory = provider_factory or self._default_provider
        self._scheduler = scheduler or QgsApplication.taskManager()
        self._registry = registry or create_m1_registry()
        self._audit = audit_logger or AuditLogger()
        self._history: list[dict[str, object]] = []
        self._task: Optional[CompletionTask] = None
        self._provider: Optional[LLMProvider] = None
        self._system = ""
        self._iterations = 0
        self._tool_errors = 0
        self._turn_id = ""

    def submit(self, prompt: str) -> None:
        """Start a model request for a user prompt.

        Args:
            prompt: Non-empty user message from the dock.
        """
        if self._task is not None:
            return
        self.messageReady.emit("user", prompt)
        key = self._secrets.get_api_key()
        if not key:
            self.messageReady.emit(
                "error", "No Anthropic API key is configured. Open Settings to add one."
            )
            return
        settings = load_settings()
        snapshot = build_layer_snapshot(self._project, settings.metric_crs)
        system = f"{_system_prompt()}\n\n<project_snapshot>{snapshot}</project_snapshot>"
        self._history.append({"role": "user", "content": prompt})
        provider = self._provider_factory(key, settings.model)
        self._provider = provider
        self._system = system
        self._iterations = 0
        self._tool_errors = 0
        self._turn_id = uuid4().hex
        self._schedule_completion()

    def _schedule_completion(self) -> None:
        if self._provider is None:
            return
        self._iterations += 1
        if self._iterations > 8:
            self._failed("Stopped after reaching the tool-call iteration limit.")
            return
        task = CompletionTask(self._provider, self._system, self._history, self._registry.specs())
        task.signals.completed.connect(self._completed)
        task.signals.failed.connect(self._failed)
        self._task = task
        self.busyChanged.emit(True)
        self._scheduler.addTask(task)

    def stop(self) -> None:
        """Cancel the active provider task."""
        if self._task is not None:
            self._task.cancel()

    def clear(self) -> None:
        """Clear local conversation history when idle."""
        if self._task is None:
            self._history.clear()

    def shutdown(self) -> None:
        """Cancel work and detach task signals before unload."""
        if self._task is not None:
            self._task.cancel()
            self._task = None

    def _completed(self, reply: LLMReply) -> None:
        self._task = None
        if reply.tool_calls:
            self._history.append(_assistant_history(reply))
            results = []
            settings = load_settings()
            context = ToolContext(self._project, never_send_samples=settings.never_send_samples)
            for call in reply.tool_calls:
                started = perf_counter()
                result = self._registry.execute(call.name, call.arguments, context)
                self._audit.record(
                    self._turn_id,
                    call.name,
                    list(call.arguments),
                    self._registry.risk_for(call.name),
                    result,
                    int((perf_counter() - started) * 1000),
                )
                self._tool_errors = self._tool_errors + 1 if not result.ok else 0
                self.messageReady.emit("tool", result.summary if result.ok else result.error)
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": call.id,
                        "content": {
                            "ok": result.ok,
                            "summary": result.summary,
                            "data": result.data,
                            "error": result.error,
                        },
                        "is_error": not result.ok,
                    }
                )
            self._history.append({"role": "user", "content": results})
            if self._tool_errors >= 3:
                self._failed("Stopped after repeated tool errors.")
                return
            self._schedule_completion()
            return
        self.busyChanged.emit(False)
        self._history.append({"role": "assistant", "content": reply.text})
        self.messageReady.emit("assistant", reply.text)

    def _failed(self, error: str) -> None:
        self._task = None
        self._provider = None
        self.busyChanged.emit(False)
        self.messageReady.emit("error", error)

    @staticmethod
    def _default_provider(api_key: str, model: str) -> LLMProvider:
        return ClaudeProvider(api_key, model, QgisHttpTransport())


def _system_prompt() -> str:
    path = Path(__file__).parents[1] / "resources" / "prompts" / "system.md"
    return path.read_text(encoding="utf-8")


def _assistant_history(reply: LLMReply) -> dict[str, Any]:
    content: list[dict[str, Any]] = []
    if reply.text:
        content.append({"type": "text", "text": reply.text})
    content.extend(
        {
            "type": "tool_use",
            "id": call.id,
            "name": call.name,
            "input": call.arguments,
        }
        for call in reply.tool_calls
    )
    return {"role": "assistant", "content": content}
