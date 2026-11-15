"""Tests for the provider worker boundary."""

from __future__ import annotations

from geoutility_copilot.core.llm.base import LLMReply
from geoutility_copilot.core.llm.fake import FakeProvider
from geoutility_copilot.core.llm.task import CompletionTask


def test_completion_task_carries_only_plain_request_data(qgis_app: object) -> None:
    task = CompletionTask(FakeProvider([LLMReply(text="ok")]), "system", [], [])
    completed: list[LLMReply] = []
    task.signals.completed.connect(completed.append)

    result = task.run()
    task.finished(result)

    assert completed[0].text == "ok"


def test_completion_task_cancel(qgis_app: object) -> None:
    task = CompletionTask(FakeProvider([LLMReply(text="unused")]), "system", [], [])
    failures: list[str] = []
    task.signals.failed.connect(failures.append)

    task.cancel()
    task.finished(False)

    assert failures == ["Request cancelled."]
