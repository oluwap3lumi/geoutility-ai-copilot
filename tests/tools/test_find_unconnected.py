"""Orphan-asset tests against deterministic utility fixtures."""

from __future__ import annotations

from pathlib import Path

from qgis.core import QgsProject, QgsVectorLayer

from geoutility_copilot.core.tools.base import Risk, ToolContext
from geoutility_copilot.core.tools.find_unconnected import FindUnconnectedTool
from geoutility_copilot.core.tools.registry import ToolRegistry

DATA = Path(__file__).parents[1] / "data" / "network.gpkg"


def _load(project: QgsProject, table: str) -> QgsVectorLayer:
    layer = QgsVectorLayer(f"{DATA}|layername={table}", table, "ogr")
    assert layer.isValid()
    project.addMapLayer(layer)
    return layer


def test_attribute_mode_finds_three_orphans_and_reports_edges(
    qgis_new_project: QgsProject,
) -> None:
    _load(qgis_new_project, "transformers_32631")
    _load(qgis_new_project, "customers_32631")

    result = FindUnconnectedTool().run(
        {
            "asset_layer": "transformers_32631",
            "related_layer": "customers_32631",
            "mode": "attribute_key",
            "asset_key": "TRANSFORMER_ID",
            "related_key": "transformer_id",
        },
        ToolContext(qgis_new_project),
    )

    assert result.ok
    assert result.data["unconnected_count"] == 3
    assert result.data["null_asset_keys"] == 1
    assert result.data["duplicate_asset_key_features"] == 2
    assert result.data["ambiguous_related_keys"] == 7


def test_create_layer_adds_only_orphans(qgis_new_project: QgsProject) -> None:
    _load(qgis_new_project, "transformers_32631")
    _load(qgis_new_project, "customers_32631")

    result = FindUnconnectedTool().run(
        {
            "asset_layer": "transformers_32631",
            "related_layer": "customers_32631",
            "mode": "attribute_key",
            "asset_key": "transformer_id",
            "related_key": "transformer_id",
            "create_layer": True,
        },
        ToolContext(qgis_new_project),
    )

    output = qgis_new_project.mapLayer(result.data["result_layer_id"])
    assert output is not None
    assert output.featureCount() == 3
    assert output.name().startswith("Unconnected")


def test_spatial_mode_matches_projected_and_geographic_fixtures(
    qgis_new_project: QgsProject,
) -> None:
    for suffix in ("32631", "4326"):
        assets = _load(qgis_new_project, f"transformers_{suffix}")
        related = _load(qgis_new_project, f"customers_{suffix}")
        result = FindUnconnectedTool().run(
            {
                "asset_layer": assets.id(),
                "related_layer": related.id(),
                "mode": "spatial",
                "tolerance_m": 20,
            },
            ToolContext(qgis_new_project),
        )
        assert result.data["unconnected_count"] == 3


def test_risk_depends_on_result_layer_creation() -> None:
    registry = ToolRegistry([FindUnconnectedTool()])

    assert registry.risk_for_call("find_unconnected", {}) is Risk.READ
    assert registry.risk_for_call("find_unconnected", {"create_layer": True}) is Risk.OUTPUT


def test_unknown_key_is_helpful(qgis_new_project: QgsProject) -> None:
    _load(qgis_new_project, "transformers_32631")
    _load(qgis_new_project, "customers_32631")

    result = FindUnconnectedTool().run(
        {
            "asset_layer": "transformers_32631",
            "related_layer": "customers_32631",
            "mode": "attribute_key",
            "asset_key": "missing",
            "related_key": "transformer_id",
        },
        ToolContext(qgis_new_project),
    )

    assert not result.ok
    assert "existing fields" in result.error
