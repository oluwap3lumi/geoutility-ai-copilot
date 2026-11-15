"""Provider-neutral LLM contracts and cancellation."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event
from typing import Any, Protocol


@dataclass(frozen=True)
class ToolCall:
    """One model-requested tool invocation."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class LLMReply:
    """Provider-neutral model response."""

    text: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    stop_reason: str = "end_turn"
    usage: dict[str, int] = field(default_factory=dict)
    request_id: str = ""


class CancelToken:
    """Thread-safe cooperative cancellation token."""

    def __init__(self) -> None:
        self._event = Event()

    def cancel(self) -> None:
        """Request cancellation."""
        self._event.set()

    def is_cancelled(self) -> bool:
        """Return whether cancellation was requested."""
        return self._event.is_set()


class LLMProvider(Protocol):
    """Interface implemented by cloud, local, and fake providers."""

    def complete(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        cancel_token: CancelToken,
    ) -> LLMReply:
        """Return the next assistant response."""
        ...


class ProviderError(RuntimeError):
    """Safe, user-facing provider failure."""


class CancelledError(ProviderError):
    """Raised when a request is cooperatively cancelled."""
