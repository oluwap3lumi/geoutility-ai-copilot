"""Strict tool registration, validation, and exception containment."""

from __future__ import annotations

from typing import Any

from geoutility_copilot.core.tools.base import Tool, ToolContext, ToolResult


class ToolRegistry:
    """Fixed registry exported to providers and used for dispatch."""

    def __init__(self, tools: list[Tool]) -> None:
        self._tools = {tool.name: tool for tool in tools}
        if len(self._tools) != len(tools):
            raise ValueError("Tool names must be unique.")

    def specs(self) -> list[dict[str, Any]]:
        """Return Claude-compatible neutral tool specifications."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in self._tools.values()
        ]

    def execute(self, name: str, args: dict[str, Any], context: ToolContext) -> ToolResult:
        """Validate and execute one registered tool without leaking exceptions."""
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(
                False,
                "Unknown tool.",
                error="Unknown tool '{}'. Available: {}.".format(
                    name, ", ".join(sorted(self._tools))
                ),
            )
        error = validate_arguments(args, tool.input_schema)
        if error:
            return ToolResult(False, "Invalid tool arguments.", error=error)
        try:
            return tool.run(args, context)
        except Exception as exc:
            return ToolResult(False, "Tool failed.", error=str(exc))


def validate_arguments(args: dict[str, Any], schema: dict[str, Any]) -> str:
    """Validate the JSON-schema subset used by v1 tool arguments."""
    if not isinstance(args, dict):
        return "Arguments must be an object."
    properties = schema.get("properties", {})
    unknown = sorted(set(args) - set(properties))
    if unknown and schema.get("additionalProperties") is False:
        return "Unknown argument(s): {}.".format(", ".join(unknown))
    missing = [name for name in schema.get("required", []) if name not in args]
    if missing:
        return "Missing required argument(s): {}.".format(", ".join(missing))
    for name, value in args.items():
        rule = properties.get(name, {})
        expected = rule.get("type")
        if expected and not _matches_type(value, expected):
            return f"Argument '{name}' must be {expected}."
        if "enum" in rule and value not in rule["enum"]:
            return "Argument '{}' must be one of: {}.".format(
                name, ", ".join(str(item) for item in rule["enum"])
            )
        if isinstance(value, (int, float)) and "minimum" in rule and value < rule["minimum"]:
            return "Argument '{}' must be at least {}.".format(name, rule["minimum"])
        if isinstance(value, str) and "maxLength" in rule and len(value) > rule["maxLength"]:
            return f"Argument '{name}' is too long."
    return ""


def _matches_type(value: Any, expected: str) -> bool:
    types = {
        "string": str,
        "boolean": bool,
        "integer": int,
        "number": (int, float),
        "object": dict,
        "array": list,
    }
    expected_type = types.get(expected)
    if expected_type is None:
        return False
    if expected in {"integer", "number"} and isinstance(value, bool):
        return False
    return isinstance(value, expected_type)
