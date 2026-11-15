"""Safety policy tests across every risk tier and approval state."""

from __future__ import annotations

import pytest

from geoutility_copilot.core.safety import SafetyAction, check_safety
from geoutility_copilot.core.tools.base import Risk


@pytest.mark.parametrize("risk", [Risk.READ, Risk.SELECTION])
@pytest.mark.parametrize("read_only", [False, True])
def test_read_and_selection_are_automatic(risk: Risk, read_only: bool) -> None:
    assert check_safety(risk, read_only).action is SafetyAction.ALLOW


@pytest.mark.parametrize("risk", [Risk.OUTPUT, Risk.MODIFY])
def test_read_only_blocks_stateful_risks(risk: Risk) -> None:
    decision = check_safety(risk, True)

    assert decision.action is SafetyAction.BLOCK
    assert "Read-only" in decision.reason


@pytest.mark.parametrize("risk", [Risk.OUTPUT, Risk.MODIFY])
def test_stateful_risks_prompt_when_not_read_only(risk: Risk) -> None:
    assert check_safety(risk, False).action is SafetyAction.PROMPT


def test_output_session_approval_is_reused() -> None:
    assert check_safety(Risk.OUTPUT, False, True).action is SafetyAction.ALLOW


def test_modify_never_reuses_session_approval() -> None:
    assert check_safety(Risk.MODIFY, False, True).action is SafetyAction.PROMPT
