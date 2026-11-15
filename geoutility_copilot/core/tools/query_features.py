"""Expression query, aggregation, and selection tool."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, ClassVar

from qgis.core import QgsExpression, QgsFeatureRequest

from geoutility_copilot.core.tools.base import Risk, ToolContext, ToolResult
from geoutility_copilot.core.tools.layers import resolve_vector_layer


class QueryFeaturesTool:
    """Query vector features with validated QGIS expressions."""

    name = "query_features"
    description = (
        "Filter one vector layer with a QGIS expression, optionally change its selection, "
        "and calculate count/sum/min/max/mean aggregates. Use real fields from inspect_layers."
    )
    risk = Risk.SELECTION
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "layer": {"type": "string", "maxLength": 200},
            "expression": {"type": "string", "maxLength": 2000},
            "select": {"type": "boolean"},
            "mode": {"type": "string", "enum": ["new", "add", "remove", "intersect"]},
            "aggregate": {"type": "string", "enum": ["count", "sum", "min", "max", "mean"]},
            "aggregate_field": {"type": "string", "maxLength": 200},
            "group_by": {"type": "string", "maxLength": 200},
            "limit": {"type": "integer", "minimum": 0},
        },
        "required": ["layer", "expression"],
        "additionalProperties": False,
    }

    def preview(self, args: dict[str, Any], context: ToolContext) -> str:
        """Describe the reversible query/selection."""
        return "Query features and optionally change the reversible map selection."

    def selection_layer_reference(self, args: dict[str, Any]) -> str:
        """Return the layer whose selection may change."""
        return str(args.get("layer", "")) if args.get("select") else ""

    def run(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        """Evaluate the expression, aggregate, and optionally select matches."""
        layer = resolve_vector_layer(context.project, str(args["layer"]))
        expression = QgsExpression(str(args["expression"]))
        if expression.hasParserError():
            return ToolResult(False, "Invalid expression.", error=expression.parserErrorString())
        fields = {field.name() for field in layer.fields()}
        missing = sorted(expression.referencedColumns() - fields)
        if missing:
            return ToolResult(
                False,
                "Expression references unknown fields.",
                error="Unknown field(s): {}. Available: {}.".format(
                    ", ".join(missing), ", ".join(sorted(fields))
                ),
            )
        for field_arg in ("aggregate_field", "group_by"):
            value = args.get(field_arg)
            if value and value not in fields:
                return ToolResult(
                    False,
                    "Unknown field.",
                    error="Field '{}' not found. Available: {}.".format(
                        value, ", ".join(sorted(fields))
                    ),
                )
        features = list(layer.getFeatures(QgsFeatureRequest(expression)))
        ids = [feature.id() for feature in features]
        previous = list(layer.selectedFeatureIds())
        if args.get("select", False):
            _apply_selection(layer, ids, str(args.get("mode", "new")))
        data: dict[str, Any] = {
            "layer": layer.name(),
            "count": len(features),
            "sample_ids": ids[: context.max_result_ids],
            "selected_count": layer.selectedFeatureCount(),
            "previous_selection_ids": previous[: context.max_result_ids],
        }
        aggregate = args.get("aggregate")
        if aggregate:
            data["aggregate"] = _aggregate(features, str(aggregate), args)
        return ToolResult(True, f"Matched {len(features)} features.", data)


def _apply_selection(layer: Any, ids: list[int], mode: str) -> None:
    current = set(layer.selectedFeatureIds())
    matches = set(ids)
    selected = {
        "new": matches,
        "add": current | matches,
        "remove": current - matches,
        "intersect": current & matches,
    }[mode]
    layer.selectByIds(list(selected))


def _aggregate(features: list[Any], operation: str, args: dict[str, Any]) -> Any:
    if operation == "count" and not args.get("group_by"):
        return len(features)
    field = args.get("aggregate_field")
    group_by = args.get("group_by")
    groups: dict[str, list[float]] = defaultdict(list)
    for feature in features:
        group = str(feature[group_by]) if group_by else "all"
        if operation == "count":
            groups[group].append(1.0)
        elif field and feature[field] is not None:
            try:
                groups[group].append(float(feature[field]))
            except (TypeError, ValueError):
                continue
    results = {group: _reduce(values, operation) for group, values in groups.items()}
    return results if group_by else results.get("all")


def _reduce(values: list[float], operation: str) -> Any:
    if not values:
        return None
    if operation == "count":
        return len(values)
    if operation == "sum":
        return sum(values)
    if operation == "min":
        return min(values)
    if operation == "max":
        return max(values)
    return sum(values) / len(values)
