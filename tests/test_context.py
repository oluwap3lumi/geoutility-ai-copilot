"""Layer-awareness snapshot tests."""

from __future__ import annotations

import json

from qgis.core import QgsField, QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import QMetaType

from geoutility_copilot.core.context import MAX_DETAILED_LAYERS, build_layer_snapshot


def test_empty_project_snapshot(qgis_new_project: QgsProject) -> None:
    payload = json.loads(build_layer_snapshot(qgis_new_project))

    assert payload["layer_count"] == 0
    assert payload["layers"] == []
    assert payload["project_crs"]


def test_vector_snapshot_contains_schema_but_no_values(qgis_new_project: QgsProject) -> None:
    layer = QgsVectorLayer("Point?crs=EPSG:32631", "DSS Transformers", "memory")
    layer.dataProvider().addAttributes(
        [
            QgsField("ASSET_ID", QMetaType.Type.QString),
            QgsField("RATED_KVA", QMetaType.Type.Int),
        ]
    )
    layer.updateFields()
    qgis_new_project.addMapLayer(layer)

    encoded = build_layer_snapshot(qgis_new_project, active_layer=layer, map_extent_available=True)
    payload = json.loads(encoded)
    details = payload["layers"][0]

    assert details["name"] == "DSS Transformers"
    assert details["geometry"] == "Point"
    assert details["crs"] == "EPSG:32631"
    assert details["provider"] == "memory"
    assert details["active"] is True
    assert [field["name"] for field in details["fields"]] == ["ASSET_ID", "RATED_KVA"]
    assert "coordinates" not in encoded


def test_layer_without_crs_is_flagged_unknown(qgis_new_project: QgsProject) -> None:
    layer = QgsVectorLayer("None", "Table", "memory")
    qgis_new_project.addMapLayer(layer)

    details = json.loads(build_layer_snapshot(qgis_new_project))["layers"][0]

    assert details["crs"] == "unknown"
    assert details["geometry"] == "NoGeometry"


def test_more_than_layer_cap_uses_identity_only_overflow(qgis_new_project: QgsProject) -> None:
    for index in range(MAX_DETAILED_LAYERS + 3):
        qgis_new_project.addMapLayer(QgsVectorLayer("Point", f"Layer {index:02d}", "memory"))

    payload = json.loads(build_layer_snapshot(qgis_new_project))

    assert len(payload["layers"]) == MAX_DETAILED_LAYERS
    assert len(payload["overflow_layers"]) == 3
    assert payload["truncated"] is True
    assert set(payload["overflow_layers"][0]) == {"id", "name", "type"}


def test_snapshot_is_deterministic(qgis_new_project: QgsProject) -> None:
    qgis_new_project.addMapLayer(QgsVectorLayer("Point", "Zulu", "memory"))
    qgis_new_project.addMapLayer(QgsVectorLayer("Point", "Alpha", "memory"))

    first = build_layer_snapshot(qgis_new_project)
    second = build_layer_snapshot(qgis_new_project)

    assert first == second
    assert [item["name"] for item in json.loads(first)["layers"]] == ["Alpha", "Zulu"]
