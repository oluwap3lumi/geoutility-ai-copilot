"""Network validation report tests against synthetic fixtures."""

from __future__ import annotations

from pathlib import Path

from qgis.core import QgsProject, QgsVectorLayer

from geoutility_copilot.core.schema_map import PROJECT_GROUP, PROJECT_KEY, SchemaMap
from geoutility_copilot.core.tools.base import Risk, ToolContext
from geoutility_copilot.core.tools.generate_report import CHECK_NAMES, GenerateReportTool

DATA = Path(__file__).parents[1] / "data" / "network.gpkg"


def _project(project: QgsProject, suffix: str = "32631") -> None:
    for base in ("transformers", "customers", "poles", "feeders"):
        table = f"{base}_{suffix}"
        layer = QgsVectorLayer(f"{DATA}|layername={table}", table, "ogr")
        assert layer.isValid()
        project.addMapLayer(layer)
    mapping = SchemaMap(
        {
            "transformer": {
                "layer": f"transformers_{suffix}",
                "id_field": "transformer_id",
                "rated_field": "rated_kva",
                "load_field": "load_kva",
                "feeder_field": "feeder_id",
            },
            "customer": {
                "layer": f"customers_{suffix}",
                "id_field": "customer_id",
                "transformer_key": "transformer_id",
                "sensitive_fields": ["name"],
            },
            "pole": {
                "layer": f"poles_{suffix}",
                "id_field": "pole_id",
                "feeder_field": "feeder_id",
            },
            "feeder_11kv": {"layer": f"feeders_{suffix}", "id_field": "feeder_id"},
        }
    )
    project.writeEntry(PROJECT_GROUP, PROJECT_KEY, mapping.to_json())


def test_report_writes_known_fixture_counts(qgis_new_project: QgsProject, tmp_path: Path) -> None:
    _project(qgis_new_project)

    result = GenerateReportTool().run(
        {"output_folder": str(tmp_path), "report_name": "validation.html"},
        ToolContext(qgis_new_project, model="test-model"),
    )

    assert result.ok
    counts = result.data["check_counts"]
    assert counts["transformers_without_customers"] == 3
    assert counts["customers_without_transformers"] == 0
    assert counts["duplicate_asset_ids"] == 2
    assert counts["missing_mandatory_attributes"] == 1
    assert counts["rated_capacity_outliers"] == 1
    assert set(counts) == set(CHECK_NAMES)
    html = (tmp_path / "validation.html").read_text(encoding="utf-8")
    assert "Network asset validation" in html
    assert "test-model" in html
    assert "QGIS" in html


def test_report_check_toggle_and_csv(qgis_new_project: QgsProject, tmp_path: Path) -> None:
    _project(qgis_new_project)

    result = GenerateReportTool().run(
        {
            "output_folder": str(tmp_path),
            "report_name": "orphans.html",
            "checks": ["transformers_without_customers"],
            "include_csv": True,
        },
        ToolContext(qgis_new_project),
    )

    assert result.data["check_counts"] == {"transformers_without_customers": 3}
    assert (tmp_path / "orphans-transformers_without_customers.csv").exists()


def test_report_refuses_overwrite(qgis_new_project: QgsProject, tmp_path: Path) -> None:
    _project(qgis_new_project)
    path = tmp_path / "existing.html"
    path.write_text("keep", encoding="utf-8")

    result = GenerateReportTool().run(
        {"output_folder": str(tmp_path), "report_name": path.name},
        ToolContext(qgis_new_project),
    )

    assert not result.ok
    assert "overwrite" in result.error
    assert path.read_text(encoding="utf-8") == "keep"


def test_report_requires_valid_confirmed_schema(
    qgis_new_project: QgsProject, tmp_path: Path
) -> None:
    qgis_new_project.writeEntry(
        PROJECT_GROUP,
        PROJECT_KEY,
        SchemaMap({"transformer": {"layer": "missing", "id_field": "id"}}).to_json(),
    )

    result = GenerateReportTool().run(
        {"output_folder": str(tmp_path), "report_name": "invalid.html"},
        ToolContext(qgis_new_project),
    )

    assert not result.ok
    assert "Schema map" in result.summary
    assert not (tmp_path / "invalid.html").exists()


def test_generate_report_is_always_output() -> None:
    assert GenerateReportTool().risk is Risk.OUTPUT
