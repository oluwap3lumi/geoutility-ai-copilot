"""CRS-safe spatial selection tool."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, ClassVar, Union

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsGeometry,
    QgsProject,
    QgsSpatialIndex,
    QgsVectorLayer,
)

from geoutility_copilot.core.tools.base import Risk, ToolContext, ToolResult
from geoutility_copilot.core.tools.expressions import expression_request
from geoutility_copilot.core.tools.layers import resolve_vector_layer


class SpatialSelectTool:
    """Select target features by an exact spatial relationship."""

    name = "spatial_select"
    description = (
        "Select target features by distance or geometry relationship to a reference layer. "
        "Use for poles within metres of a feeder; not for attribute-only filters."
    )
    risk = Risk.SELECTION
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "target_layer": {"type": "string", "maxLength": 200},
            "reference_layer": {"type": "string", "maxLength": 200},
            "relationship": {
                "type": "string",
                "enum": ["within_distance", "intersects", "within", "contains"],
            },
            "distance_m": {"type": "number", "minimum": 0},
            "reference_selected_only": {"type": "boolean"},
            "reference_expression": {"type": "string", "maxLength": 2000},
        },
        "required": ["target_layer", "reference_layer", "relationship"],
        "additionalProperties": False,
    }

    def preview(self, args: dict[str, Any], context: ToolContext) -> str:
        """Describe the reversible target selection."""
        return "Select features in '{}' using '{}' against '{}'.".format(
            args.get("target_layer", "?"),
            args.get("relationship", "?"),
            args.get("reference_layer", "?"),
        )

    def selection_layer_reference(self, args: dict[str, Any]) -> str:
        """Return the target layer whose selection changes."""
        return str(args.get("target_layer", ""))

    def run(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        """Execute the spatial selection on the QGIS main thread."""
        target = resolve_vector_layer(context.project, str(args["target_layer"]))
        reference = resolve_vector_layer(context.project, str(args["reference_layer"]))
        relationship = str(args["relationship"])
        if relationship == "within_distance" and "distance_m" not in args:
            return ToolResult(False, "Missing distance.", error="distance_m is required.")
        if not target.crs().isValid() or not reference.crs().isValid():
            return ToolResult(False, "Invalid layer CRS.", error="Both layers need a valid CRS.")
        metric = QgsCoordinateReferenceSystem(context.metric_crs)
        if not metric.isValid() or metric.isGeographic():
            return ToolResult(False, "Invalid metric CRS.", error="Metric CRS must be projected.")
        references = _reference_features(reference, args)
        if isinstance(references, str):
            return ToolResult(False, "Invalid reference filter.", error=references)
        selected = _matching_ids(
            target,
            reference,
            references,
            metric,
            relationship,
            float(args.get("distance_m", 0)),
            context.project,
        )
        target.selectByIds(selected)
        return ToolResult(
            True,
            f"Selected {len(selected)} features in '{target.name()}'.",
            {"selected_count": len(selected), "sample_ids": selected[: context.max_result_ids]},
        )


def _reference_features(
    layer: QgsVectorLayer, args: dict[str, Any]
) -> Union[Iterable[QgsFeature], str]:  # noqa: UP007 - QGIS 3.34 supports Python 3.9
    expression_text = str(args.get("reference_expression", "")).strip()
    if expression_text:
        request = expression_request(layer, expression_text)
        return request if isinstance(request, str) else layer.getFeatures(request)
    if args.get("reference_selected_only"):
        return layer.getSelectedFeatures()
    return layer.getFeatures()


def _matching_ids(
    target: QgsVectorLayer,
    reference: QgsVectorLayer,
    references: Iterable[QgsFeature],
    metric: QgsCoordinateReferenceSystem,
    relationship: str,
    distance: float,
    project: QgsProject,
) -> list[int]:
    target_transform = QgsCoordinateTransform(target.crs(), metric, project)
    reference_transform = QgsCoordinateTransform(reference.crs(), metric, project)
    geometries: dict[int, QgsGeometry] = {}
    index = QgsSpatialIndex()
    for feature in target.getFeatures():
        if not feature.hasGeometry() or feature.geometry().isNull():
            continue
        geometry = QgsGeometry(feature.geometry())
        geometry.transform(target_transform)
        indexed = QgsFeature(feature.id())
        indexed.setGeometry(geometry)
        index.addFeature(indexed)
        geometries[feature.id()] = geometry
    matched: set[int] = set()
    for feature in references:
        if not feature.hasGeometry() or feature.geometry().isNull():
            continue
        reference_geometry = QgsGeometry(feature.geometry())
        reference_geometry.transform(reference_transform)
        bounds = reference_geometry.boundingBox()
        if relationship == "within_distance":
            bounds.grow(distance + 0.01)
        for feature_id in index.intersects(bounds):
            if _matches(geometries[feature_id], reference_geometry, relationship, distance):
                matched.add(feature_id)
    return sorted(matched)


def _matches(
    target: QgsGeometry, reference: QgsGeometry, relationship: str, distance: float
) -> bool:
    if relationship == "within_distance":
        # GeoPackage round-tripping through EPSG:4326 introduces sub-centimetre boundary noise.
        return target.distance(reference) <= distance + 0.01
    if relationship == "intersects":
        return target.intersects(reference)
    if relationship == "within":
        return target.within(reference)
    return target.contains(reference)
