"""Project layer inspection tool."""

from __future__ import annotations

from typing import Any, ClassVar

from qgis.core import QgsVectorLayer, QgsWkbTypes

from geoutility_copilot.core.schema_map import (
    SchemaMap,
    load_schema_map,
    roles_for_layer,
    sensitive_fields_for_layer,
)
from geoutility_copilot.core.tools.base import Risk, ToolContext, ToolResult
from geoutility_copilot.core.tools.layers import resolve_vector_layer

SENSITIVE_PARTS = ("name", "phone", "address", "meter")


class InspectLayersTool:
    """Return layer inventory or one detailed vector schema."""

    name = "inspect_layers"
    description = (
        "Inspect project layers and schemas. Use this before assuming layer or field names. "
        "Returns confirmed schema roles and selected counts needed to resolve phrases such as "
        "'this feeder'. Do not use it to calculate statistics or select features."
    )
    risk = Risk.READ
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "layer": {"type": "string", "maxLength": 200},
            "include_samples": {"type": "boolean"},
        },
        "additionalProperties": False,
    }

    def preview(self, args: dict[str, Any], context: ToolContext) -> str:
        """Describe the read-only inspection."""
        return "Inspect project layer metadata without changing the project."

    def run(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        """Inspect all layers or one resolved vector layer."""
        reference = args.get("layer")
        if reference:
            layer = resolve_vector_layer(context.project, str(reference))
            mapping = load_schema_map(context.project)
            data = _vector_details(layer, bool(args.get("include_samples")), context, mapping)
            return ToolResult(True, f"Inspected layer '{layer.name()}'.", data)
        layers = []
        mapping = load_schema_map(context.project)
        for layer in sorted(
            context.project.mapLayers().values(), key=lambda item: item.name().casefold()
        ):
            item = {
                "id": layer.id(),
                "name": layer.name(),
                "provider": layer.providerType(),
                "crs": layer.crs().authid() or "unknown",
                "type": "vector" if isinstance(layer, QgsVectorLayer) else "non_vector",
            }
            if isinstance(layer, QgsVectorLayer):
                item.update(
                    {
                        "geometry": QgsWkbTypes.displayString(layer.wkbType()),
                        "feature_count": layer.featureCount(),
                        "selected_count": layer.selectedFeatureCount(),
                        "roles": roles_for_layer(mapping, layer),
                    }
                )
            layers.append(item)
        return ToolResult(True, f"Found {len(layers)} project layers.", {"layers": layers})


def _vector_details(
    layer: QgsVectorLayer, include_samples: bool, context: ToolContext, mapping: SchemaMap
) -> dict[str, Any]:
    fields = [{"name": field.name(), "type": field.typeName()} for field in layer.fields()]
    samples = []
    configured_sensitive = sensitive_fields_for_layer(mapping, layer)
    if include_samples and not context.never_send_samples:
        for feature in layer.getFeatures():
            row = {}
            for field in layer.fields():
                value = feature[field.name()]
                row[field.name()] = (
                    "[sensitive]"
                    if field.name().casefold() in configured_sensitive
                    or any(part in field.name().casefold() for part in SENSITIVE_PARTS)
                    else str(value)[:40]
                )
            samples.append(row)
            if len(samples) >= context.max_samples:
                break
    return {
        "id": layer.id(),
        "name": layer.name(),
        "geometry": QgsWkbTypes.displayString(layer.wkbType()),
        "crs": layer.crs().authid() or "unknown",
        "provider": layer.providerType(),
        "feature_count": layer.featureCount(),
        "selected_count": layer.selectedFeatureCount(),
        "fields": fields,
        "roles": roles_for_layer(mapping, layer),
        "samples": samples,
    }
