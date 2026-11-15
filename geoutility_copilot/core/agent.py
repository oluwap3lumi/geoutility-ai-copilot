"""Provider-neutral bounded tool-use loop."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from geoutility_copilot.core.llm.base import (
    CancelledError,
    CancelToken,
    LLMProvider,
    LLMReply,
)

ToolExecutor = Callable[[str, dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class AgentResult:
    """Completed user turn and the messages it produced."""

    text: str
    messages: tuple[dict[str, Any], ...]
    iterations: int
    cancelled: bool = False


class AgentLoop:
    """Run model/tool rounds with hard iteration and error limits."""

    def __init__(
        self,
        provider: LLMProvider,
        tool_executor: ToolExecutor,
        max_iterations: int = 8,
        max_consecutive_errors: int = 3,
    ) -> None:
        """Configure the bounded loop.

        Args:
            provider: Provider-neutral completion service.
            tool_executor: Main-thread callback for registered tools.
            max_iterations: Maximum model calls per user turn.
            max_consecutive_errors: Tool failures allowed before stopping.
        """
        self._provider = provider
        self._tool_executor = tool_executor
        self._max_iterations = max_iterations
        self._max_errors = max_consecutive_errors

    def run_turn(
        self,
        system: str,
        history: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        cancel_token: Optional[CancelToken] = None,
    ) -> AgentResult:
        """Run one user turn until text, cancellation, or a hard cap.

        Args:
            system: System prompt plus current project snapshot.
            history: Mutable-neutral message history copied by this method.
            tools: Provider-neutral tool specifications.
            cancel_token: Cooperative cancellation token.
        """
        token = cancel_token or CancelToken()
        messages = list(history)
        consecutive_errors = 0
        for iteration in range(1, self._max_iterations + 1):
            if token.is_cancelled():
                return AgentResult("Request cancelled.", tuple(messages), iteration - 1, True)
            try:
                reply = self._provider.complete(system, messages, tools, token)
            except CancelledError:
                return AgentResult("Request cancelled.", tuple(messages), iteration - 1, True)
            messages.append(_assistant_message(reply))
            if not reply.tool_calls:
                return AgentResult(reply.text, tuple(messages), iteration)
            tool_results = []
            for call in reply.tool_calls:
                if token.is_cancelled():
                    return AgentResult("Request cancelled.", tuple(messages), iteration, True)
                result = self._run_tool(call.name, call.arguments)
                consecutive_errors = consecutive_errors + 1 if not result["ok"] else 0
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": call.id,
                        "content": result,
                        "is_error": not result["ok"],
                    }
                )
                if consecutive_errors >= self._max_errors:
                    messages.append({"role": "user", "content": tool_results})
                    return AgentResult(
                        "Stopped after repeated tool errors.", tuple(messages), iteration
                    )
            messages.append({"role": "user", "content": tool_results})
        return AgentResult(
            "Stopped after reaching the tool-call iteration limit.",
            tuple(messages),
            self._max_iterations,
        )

    def _run_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            result = self._tool_executor(name, arguments)
            return {"ok": True, "result": result}
        except Exception as exc:  # tool failures are structured data for model recovery
            return {"ok": False, "error": str(exc)}


def _assistant_message(reply: LLMReply) -> dict[str, Any]:
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
