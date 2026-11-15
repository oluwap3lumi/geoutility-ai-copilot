"""Main-thread controller tests with synchronous fake scheduling."""

from __future__ import annotations

from geoutility_copilot.core.controller import AgentController
from geoutility_copilot.core.llm.base import LLMReply, ToolCall
from geoutility_copilot.core.llm.fake import FakeProvider
from geoutility_copilot.core.llm.task import CompletionTask


class FakeSecrets:
    def __init__(self, key: str) -> None:
        self.key = key

    def has_api_key(self) -> bool:
        return bool(self.key)

    def get_api_key(self) -> str:
        return self.key

    def set_api_key(self, api_key: str) -> None:
        self.key = api_key


class ImmediateScheduler:
    def addTask(self, task: CompletionTask) -> None:
        result = task.run()
        task.finished(result)


def test_missing_key_is_friendly(qgis_new_project: object) -> None:
    controller = AgentController(
        project=qgis_new_project, secret_store=FakeSecrets(""), scheduler=ImmediateScheduler()
    )
    messages: list[tuple[str, str]] = []
    controller.messageReady.connect(lambda role, text: messages.append((role, text)))

    controller.submit("hello")

    assert messages[0] == ("user", "hello")
    assert messages[1][0] == "error"
    assert "API key" in messages[1][1]


def test_plain_provider_reply_reaches_ui(qgis_new_project: object) -> None:
    provider = FakeProvider([LLMReply(text="Hello from provider")])
    controller = AgentController(
        project=qgis_new_project,
        secret_store=FakeSecrets("key"),
        provider_factory=lambda key, model: provider,
        scheduler=ImmediateScheduler(),
    )
    messages: list[tuple[str, str]] = []
    busy: list[bool] = []
    controller.messageReady.connect(lambda role, text: messages.append((role, text)))
    controller.busyChanged.connect(busy.append)

    controller.submit("hello")

    assert messages[-1] == ("assistant", "Hello from provider")
    assert busy == [True, False]
    assert "project_snapshot" in provider.requests[0]["system"]


def test_tool_round_executes_on_controller_thread(qgis_new_project: object) -> None:
    provider = FakeProvider(
        [
            LLMReply(tool_calls=(ToolCall("1", "inspect_layers", {}),)),
            LLMReply(text="There are no layers."),
        ]
    )
    controller = AgentController(
        project=qgis_new_project,
        secret_store=FakeSecrets("key"),
        provider_factory=lambda key, model: provider,
        scheduler=ImmediateScheduler(),
    )
    messages: list[tuple[str, str]] = []
    controller.messageReady.connect(lambda role, text: messages.append((role, text)))

    controller.submit("what layers")

    assert any(role == "tool" for role, text in messages)
    assert messages[-1] == ("assistant", "There are no layers.")
    assert len(provider.requests) == 2
