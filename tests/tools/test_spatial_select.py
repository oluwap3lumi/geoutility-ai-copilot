"""Spatial selection tests against deterministic projected/geographic fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
from qgis.core import QgsProject, QgsVectorLayer

from geoutility_copilot.core.tools.base import ToolContext
from geoutility_copilot.core.tools.spatial_select import SpatialSelectTool

DATA = Path(__file__).parents[1] / "data" / "network.gpkg"


def _load(project: QgsProject, table: str) -> QgsVectorLayer:
    layer = QgsVectorLayer(f"{DATA}|layername={table}", table, "ogr")
    assert layer.isValid()
    project.addMapLayer(layer)
    return layer


@pytest.mark.parametrize("suffix", ["32631", "4326"])
def test_within_50_metres_matches_across_crs(qgis_new_project: QgsProject, suffix: str) -> None:
    poles = _load(qgis_new_project, f"poles_{suffix}")
    _load(qgis_new_project, f"feeders_{suffix}")

    result = SpatialSelectTool().run(
        {
            "target_layer": poles.name(),
            "reference_layer": f"feeders_{suffix}",
            "relationship": "within_distance",
            "distance_m": 50,
            "reference_expression": "\"feeder_id\" = 'F01'",
        },
        ToolContext(qgis_new_project),
    )

    assert result.ok
    assert result.data["selected_count"] == 9
    assert poles.selectedFeatureCount() == 9


def test_selected_reference_only(qgis_new_project: QgsProject) -> None:
    poles = _load(qgis_new_project, "poles_32631")
    feeders = _load(qgis_new_project, "feeders_32631")
    feeders.selectByIds([next(feeders.getFeatures()).id()])

    result = SpatialSelectTool().run(
        {
            "target_layer": poles.id(),
            "reference_layer": feeders.id(),
            "relationship": "within_distance",
            "distance_m": 50,
            "reference_selected_only": True,
        },
        ToolContext(qgis_new_project),
    )

    assert result.data["selected_count"] == 9


def test_bad_reference_expression_is_structured(qgis_new_project: QgsProject) -> None:
    _load(qgis_new_project, "poles_32631")
    _load(qgis_new_project, "feeders_32631")

    result = SpatialSelectTool().run(
        {
            "target_layer": "poles_32631",
            "reference_layer": "feeders_32631",
            "relationship": "intersects",
            "reference_expression": '"feeder_id" =',
        },
        ToolContext(qgis_new_project),
    )

    assert not result.ok
    assert "expression" in result.error


def test_missing_distance_is_rejected(qgis_new_project: QgsProject) -> None:
    _load(qgis_new_project, "poles_32631")
    _load(qgis_new_project, "feeders_32631")

    result = SpatialSelectTool().run(
        {
            "target_layer": "poles_32631",
            "reference_layer": "feeders_32631",
            "relationship": "within_distance",
        },
        ToolContext(qgis_new_project),
    )

    assert result.error == "distance_m is required."
