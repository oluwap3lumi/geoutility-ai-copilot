"""Tool-risk policy enforced independently of model instructions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from geoutility_copilot.core.tools.base import Risk


class SafetyAction(str, Enum):
    """Action the controller must take before tool execution."""

    ALLOW = "allow"
    PROMPT = "prompt"
    BLOCK = "block"


@dataclass(frozen=True)
class SafetyDecision:
    """Policy outcome with a user-safe explanation."""

    action: SafetyAction
    reason: str


@dataclass(frozen=True)
class ApprovalRequest:
    """Human-readable details for one proposed tool call."""

    tool: str
    risk: Risk
    preview: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ApprovalResponse:
    """One explicit user decision."""

    approved: bool
    approve_session: bool = False


def check_safety(
    risk: Risk, read_only: bool, output_session_approved: bool = False
) -> SafetyDecision:
    """Evaluate one tool risk against the current safety state."""
    if read_only and risk in {Risk.OUTPUT, Risk.MODIFY}:
        return SafetyDecision(SafetyAction.BLOCK, "Read-only mode blocks output and modify tools.")
    if risk in {Risk.READ, Risk.SELECTION}:
        return SafetyDecision(SafetyAction.ALLOW, "Allowed automatically.")
    if risk is Risk.OUTPUT and output_session_approved:
        return SafetyDecision(SafetyAction.ALLOW, "Approved for this chat session.")
    return SafetyDecision(SafetyAction.PROMPT, "Explicit user approval is required.")
