"""Build compact, deterministic QGIS project snapshots."""

from __future__ import annotations

import json
from typing import Any, Optional

from qgis.core import Qgis, QgsMapLayer, QgsProject, QgsVectorLayer, QgsWkbTypes

MAX_DETAILED_LAYERS = 40


def build_layer_snapshot(
    project: QgsProject,
    metric_crs: str = "EPSG:32631",
    active_layer: Optional[QgsMapLayer] = None,
    map_extent_available: bool = False,
) -> str:
    """Return a privacy-safe JSON snapshot of the current project.

    Args:
        project: QGIS project whose layers should be described.
        metric_crs: Configured CRS for metre-based operations.
        active_layer: Currently active map layer, when available.
        map_extent_available: Whether a map extent exists; coordinates are not included.
    """
    layers = sorted(
        project.mapLayers().values(), key=lambda layer: (layer.name().casefold(), layer.id())
    )
    detailed = layers[:MAX_DETAILED_LAYERS]
    overflow = layers[MAX_DETAILED_LAYERS:]
    payload = {
        "project_crs": _crs_auth_id(project.crs()),
        "metric_crs_setting": metric_crs,
        "layer_count": len(layers),
        "map_extent_available": map_extent_available,
        "layers": [_layer_details(layer, active_layer) for layer in detailed],
        "overflow_layers": [
            {"name": layer.name(), "id": layer.id(), "type": _layer_type(layer)}
            for layer in overflow
        ],
        "truncated": bool(overflow),
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _layer_details(layer: QgsMapLayer, active_layer: Optional[QgsMapLayer]) -> dict[str, Any]:
    details: dict[str, Any] = {
        "name": layer.name(),
        "id": layer.id(),
        "type": _layer_type(layer),
        "crs": _crs_auth_id(layer.crs()),
        "provider": layer.providerType(),
        "active": active_layer is not None and layer.id() == active_layer.id(),
    }
    if isinstance(layer, QgsVectorLayer):
        details.update(
            {
                "geometry": QgsWkbTypes.displayString(layer.wkbType()),
                "feature_count": _known_feature_count(layer.featureCount()),
                "selected_count": layer.selectedFeatureCount(),
                "fields": [
                    {"name": field.name(), "type": field.typeName()} for field in layer.fields()
                ],
            }
        )
    else:
        details.update(
            {
                "geometry": None,
                "feature_count": None,
                "selected_count": None,
                "fields": [],
            }
        )
    return details


def _layer_type(layer: QgsMapLayer) -> str:
    layer_type = layer.type()
    known_names = (
        ("Vector", "vector"),
        ("Raster", "raster"),
        ("Mesh", "mesh"),
        ("VectorTile", "vector_tile"),
        ("PointCloud", "point_cloud"),
        ("Annotation", "annotation"),
        ("Group", "group"),
        ("TiledScene", "tiled_scene"),
    )
    for enum_name, label in known_names:
        enum_value = getattr(Qgis.LayerType, enum_name, None)
        if enum_value is not None and layer_type == enum_value:
            return label
    return "other"


def _crs_auth_id(crs: Any) -> str:
    auth_id = crs.authid()
    return auth_id if crs.isValid() and auth_id else "unknown"


def _known_feature_count(count: int) -> Optional[int]:
    return count if count >= 0 else None
