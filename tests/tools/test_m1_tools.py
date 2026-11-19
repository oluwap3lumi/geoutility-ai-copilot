"""Real PyQGIS tests for the two Milestone 1 tools."""

from __future__ import annotations

import pytest
from qgis.core import QgsFeature, QgsField, QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import QMetaType

from geoutility_copilot.core.tools import create_m1_registry
from geoutility_copilot.core.tools.base import ToolContext


def _asset_layer() -> QgsVectorLayer:
    layer = QgsVectorLayer("Point?crs=EPSG:32631", "Transformers", "memory")
    layer.dataProvider().addAttributes(
        [
            QgsField("asset_id", QMetaType.Type.QString),
            QgsField("rating", QMetaType.Type.Int),
            QgsField("load", QMetaType.Type.Double),
            QgsField("feeder", QMetaType.Type.QString),
        ]
    )
    layer.updateFields()
    rows = [
        ("T1", 100, 90.0, "F1"),
        ("T2", 200, 250.0, "F1"),
        ("T3", 300, 100.0, "F2"),
    ]
    features = []
    for row in rows:
        feature = QgsFeature(layer.fields())
        feature.setAttributes(list(row))
        features.append(feature)
    layer.dataProvider().addFeatures(features)
    return layer


def test_inspect_layers_and_schema_only_samples(qgis_new_project: QgsProject) -> None:
    layer = _asset_layer()
    qgis_new_project.addMapLayer(layer)
    registry = create_m1_registry()
    context = ToolContext(qgis_new_project, never_send_samples=True)

    inventory = registry.execute("inspect_layers", {}, context)
    details = registry.execute(
        "inspect_layers", {"layer": "transformers", "include_samples": True}, context
    )

    assert inventory.ok
    assert inventory.data["layers"][0]["feature_count"] == 3
    assert details.data["samples"] == []
    assert [field["name"] for field in details.data["fields"]] == [
        "asset_id",
        "rating",
        "load",
        "feeder",
    ]


def test_query_select_and_aggregate(qgis_new_project: QgsProject) -> None:
    layer = _asset_layer()
    qgis_new_project.addMapLayer(layer)
    registry = create_m1_registry()
    context = ToolContext(qgis_new_project)

    selected = registry.execute(
        "query_features",
        {
            "layer": layer.id(),
            "expression": '"load" > "rating"',
            "select": True,
            "mode": "new",
        },
        context,
    )
    aggregate = registry.execute(
        "query_features",
        {
            "layer": "Transformers",
            "expression": '"rating" >= 0',
            "aggregate": "mean",
            "aggregate_field": "load",
            "group_by": "feeder",
        },
        context,
    )

    assert selected.ok
    assert selected.data["count"] == 1
    assert layer.selectedFeatureCount() == 1
    assert aggregate.data["aggregate"] == {"F1": 170.0, "F2": 100.0}


def test_query_errors_are_actionable(qgis_new_project: QgsProject) -> None:
    layer = _asset_layer()
    qgis_new_project.addMapLayer(layer)
    registry = create_m1_registry()
    context = ToolContext(qgis_new_project)
    previous = [next(layer.getFeatures()).id()]
    layer.selectByIds(previous)

    missing_layer = registry.execute(
        "query_features", {"layer": "Missing", "expression": "1=1"}, context
    )
    bad_expression = registry.execute(
        "query_features", {"layer": layer.id(), "expression": '"rating" >', "select": True}, context
    )
    bad_field = registry.execute(
        "query_features", {"layer": layer.id(), "expression": '"nope" = 1', "select": True}, context
    )

    assert not missing_layer.ok and "Available" in missing_layer.error
    assert not bad_expression.ok and bad_expression.error
    assert not bad_field.ok and "Available" in bad_field.error
    assert layer.selectedFeatureIds() == previous


@pytest.mark.parametrize("expression", ['"RATING" >= 200', "attribute(@feature, 'rating') >= 200"])
def test_query_uses_qgis_field_resolution(qgis_new_project: QgsProject, expression: str) -> None:
    layer = _asset_layer()
    qgis_new_project.addMapLayer(layer)

    result = create_m1_registry().execute(
        "query_features",
        {"layer": layer.id(), "expression": expression, "select": True},
        ToolContext(qgis_new_project),
    )

    assert result.ok
    assert result.data["count"] == 2
    assert {feature["asset_id"] for feature in layer.getSelectedFeatures()} == {"T2", "T3"}


def test_registry_rejects_unknown_arguments(qgis_new_project: QgsProject) -> None:
    result = create_m1_registry().execute(
        "inspect_layers", {"unexpected": True}, ToolContext(qgis_new_project)
    )

    assert not result.ok
    assert "Unknown argument" in result.error
