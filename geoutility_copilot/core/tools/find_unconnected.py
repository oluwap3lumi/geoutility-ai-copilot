"""Find assets without related features by key or spatial proximity."""

from __future__ import annotations

from collections import Counter
from typing import Any, ClassVar, Optional

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsGeometry,
    QgsSpatialIndex,
    QgsVariantUtils,
    QgsVectorLayer,
    QgsWkbTypes,
)

from geoutility_copilot.core.tools.base import Risk, ToolContext, ToolResult
from geoutility_copilot.core.tools.layers import resolve_vector_layer


class FindUnconnectedTool:
    """Find orphan assets and optionally add a temporary result layer."""

    name = "find_unconnected"
    description = (
        "Find assets with no related records by matching keys or spatial tolerance. "
        "Use create_layer only when the user wants an orphan result layer; count-only is read-only."
    )
    risk = Risk.OUTPUT
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "asset_layer": {"type": "string", "maxLength": 200},
            "related_layer": {"type": "string", "maxLength": 200},
            "mode": {"type": "string", "enum": ["attribute_key", "spatial"]},
            "asset_key": {"type": "string", "maxLength": 200},
            "related_key": {"type": "string", "maxLength": 200},
            "trim_keys": {"type": "boolean"},
            "case_insensitive": {"type": "boolean"},
            "tolerance_m": {"type": "number", "minimum": 0},
            "create_layer": {"type": "boolean"},
            "result_layer_name": {"type": "string", "maxLength": 200},
        },
        "required": ["asset_layer", "related_layer", "mode"],
        "additionalProperties": False,
    }

    def risk_for_args(self, args: dict[str, Any]) -> Risk:
        """Require approval only when adding a result layer."""
        return Risk.OUTPUT if args.get("create_layer") else Risk.READ

    def preview(self, args: dict[str, Any], context: ToolContext) -> str:
        """Describe whether the call counts or creates orphan output."""
        action = "Add a temporary orphan layer" if args.get("create_layer") else "Count orphans"
        return f"{action} from '{args.get('asset_layer', '?')}' related to '{args.get('related_layer', '?')}'."

    def run(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        """Find unconnected asset features on the main thread."""
        assets = resolve_vector_layer(context.project, str(args["asset_layer"]))
        related = resolve_vector_layer(context.project, str(args["related_layer"]))
        mode = str(args["mode"])
        if mode == "attribute_key":
            outcome = _by_key(assets, related, args)
            if isinstance(outcome, str):
                return ToolResult(False, "Invalid key mapping.", error=outcome)
            orphan_ids, diagnostics = outcome
        else:
            if "tolerance_m" not in args:
                return ToolResult(False, "Missing tolerance.", error="tolerance_m is required.")
            outcome = _by_space(assets, related, float(args["tolerance_m"]), context)
            if isinstance(outcome, str):
                return ToolResult(False, "Spatial matching failed.", error=outcome)
            orphan_ids = outcome
            diagnostics = {
                "null_asset_keys": 0,
                "duplicate_asset_key_features": 0,
                "ambiguous_related_keys": 0,
            }
        data: dict[str, Any] = {
            "unconnected_count": len(orphan_ids),
            "sample_ids": orphan_ids[: context.max_result_ids],
            **diagnostics,
        }
        if args.get("create_layer"):
            result = _create_result_layer(
                assets, orphan_ids, str(args.get("result_layer_name", ""))
            )
            context.project.addMapLayer(result)
            data.update({"result_layer_id": result.id(), "result_layer_name": result.name()})
        return ToolResult(True, f"Found {len(orphan_ids)} unconnected assets.", data)


def _field_name(layer: QgsVectorLayer, requested: Any) -> Optional[str]:
    name = str(requested or "").casefold()
    matches = [field.name() for field in layer.fields() if field.name().casefold() == name]
    return matches[0] if len(matches) == 1 else None


def _normalizer(trim: bool, case_insensitive: bool) -> Any:
    def normalize(value: Any) -> Optional[str]:
        if value is None or QgsVariantUtils.isNull(value):
            return None
        text = str(value)
        if trim:
            text = text.strip()
        if not text:
            return None
        return text.casefold() if case_insensitive else text

    return normalize


def _by_key(assets: QgsVectorLayer, related: QgsVectorLayer, args: dict[str, Any]) -> Any:
    asset_key = _field_name(assets, args.get("asset_key"))
    related_key = _field_name(related, args.get("related_key"))
    if asset_key is None or related_key is None:
        return "asset_key and related_key must name existing fields."
    normalize = _normalizer(args.get("trim_keys", True), args.get("case_insensitive", True))
    asset_values = [
        (feature.id(), normalize(feature[asset_key])) for feature in assets.getFeatures()
    ]
    related_values = [normalize(feature[related_key]) for feature in related.getFeatures()]
    asset_counts = Counter(value for _, value in asset_values if value is not None)
    related_counts = Counter(value for value in related_values if value is not None)
    orphan_ids = [
        feature_id
        for feature_id, value in asset_values
        if value is None or value not in related_counts
    ]
    diagnostics = {
        "null_asset_keys": sum(value is None for _, value in asset_values),
        "duplicate_asset_key_features": sum(count for count in asset_counts.values() if count > 1),
        "ambiguous_related_keys": sum(1 for count in related_counts.values() if count > 1),
    }
    return orphan_ids, diagnostics


def _by_space(
    assets: QgsVectorLayer, related: QgsVectorLayer, tolerance: float, context: ToolContext
) -> Any:
    metric = QgsCoordinateReferenceSystem(context.metric_crs)
    if (
        not metric.isValid()
        or metric.isGeographic()
        or not assets.crs().isValid()
        or not related.crs().isValid()
    ):
        return "Both layers and the configured projected metric CRS must be valid."
    asset_transform = QgsCoordinateTransform(assets.crs(), metric, context.project)
    related_transform = QgsCoordinateTransform(related.crs(), metric, context.project)
    related_geometries: dict[int, QgsGeometry] = {}
    index = QgsSpatialIndex()
    for feature in related.getFeatures():
        if not feature.hasGeometry() or feature.geometry().isNull():
            continue
        geometry = QgsGeometry(feature.geometry())
        geometry.transform(related_transform)
        indexed = QgsFeature(feature.id())
        indexed.setGeometry(geometry)
        index.addFeature(indexed)
        related_geometries[feature.id()] = geometry
    orphans = []
    for asset in assets.getFeatures():
        if not asset.hasGeometry() or asset.geometry().isNull():
            orphans.append(asset.id())
            continue
        geometry = QgsGeometry(asset.geometry())
        geometry.transform(asset_transform)
        bounds = geometry.boundingBox()
        bounds.grow(tolerance + 0.01)
        connected = any(
            geometry.distance(related_geometries[feature_id]) <= tolerance + 0.01
            for feature_id in index.intersects(bounds)
        )
        if not connected:
            orphans.append(asset.id())
    return orphans


def _create_result_layer(
    source: QgsVectorLayer, feature_ids: list[int], requested: str
) -> QgsVectorLayer:
    name = requested.strip() or f"Unconnected — {source.name()}"
    geometry = QgsWkbTypes.displayString(source.wkbType())
    result = QgsVectorLayer(f"{geometry}?crs={source.crs().authid()}", name, "memory")
    result.dataProvider().addAttributes(list(source.fields()))
    result.updateFields()
    copies = []
    wanted = set(feature_ids)
    for source_feature in source.getFeatures():
        if source_feature.id() not in wanted:
            continue
        feature = QgsFeature(result.fields())
        feature.setAttributes(source_feature.attributes())
        feature.setGeometry(QgsGeometry(source_feature.geometry()))
        copies.append(feature)
    result.dataProvider().addFeatures(copies)
    return result
