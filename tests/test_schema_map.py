"""Semantic schema-map parsing, validation, and persistence tests."""

from __future__ import annotations

import json

import pytest
from qgis.core import QgsField, QgsProject, QgsSettings, QgsVectorLayer
from qgis.PyQt.QtCore import QMetaType

from geoutility_copilot.core.schema_map import (
    GLOBAL_KEY,
    SchemaMap,
    load_schema_map,
    parse_schema_map,
    propose_schema_map,
    roles_for_layer,
    save_schema_map,
    sensitive_fields_for_layer,
    validate_schema_map,
)


def _layer(name: str, fields: list[str]) -> QgsVectorLayer:
    layer = QgsVectorLayer("Point?crs=EPSG:32631", name, "memory")
    layer.dataProvider().addAttributes(
        [QgsField(field, QMetaType.Type.QString) for field in fields]
    )
    layer.updateFields()
    return layer


def test_packaged_default_schema_map_is_valid_json() -> None:
    mapping = load_schema_map(QgsProject())

    assert mapping.metric_crs == "EPSG:32631"
    assert set(mapping.roles) == {"transformer", "customer", "pole", "feeder_11kv"}


def test_parse_rejects_invalid_shapes() -> None:
    with pytest.raises(ValueError, match="valid JSON"):
        parse_schema_map("{")
    with pytest.raises(ValueError, match="roles"):
        parse_schema_map("{}")
    with pytest.raises(ValueError, match="layer"):
        parse_schema_map('{"roles":{"pole":{}}}')


def test_validation_is_case_insensitive_and_checks_sensitive_fields(
    qgis_new_project: QgsProject,
) -> None:
    layer = _layer("DSS Transformers", ["ASSET_ID", "NAME"])
    qgis_new_project.addMapLayer(layer)
    mapping = SchemaMap(
        {
            "transformer": {
                "layer": "dss transformers",
                "id_field": "asset_id",
                "sensitive_fields": ["name"],
            }
        }
    )

    assert validate_schema_map(mapping, qgis_new_project) == []
    assert roles_for_layer(mapping, layer) == ["transformer"]
    assert sensitive_fields_for_layer(mapping, layer) == {"name"}


def test_validation_reports_missing_layer_and_field(qgis_new_project: QgsProject) -> None:
    qgis_new_project.addMapLayer(_layer("Poles", ["pole_id"]))
    mapping = SchemaMap(
        {
            "pole": {"layer": "Poles", "feeder_field": "missing"},
            "customer": {"layer": "Customers", "id_field": "customer_id"},
        }
    )

    errors = validate_schema_map(mapping, qgis_new_project)

    assert "Role 'pole' field 'missing' does not exist." in errors
    assert "Role 'customer' layer 'Customers' was not found uniquely." in errors


def test_project_schema_map_overrides_global(qgis_new_project: QgsProject) -> None:
    QgsSettings().remove(GLOBAL_KEY)
    global_map = SchemaMap({"pole": {"layer": "Global poles"}})
    project_map = SchemaMap({"pole": {"layer": "Project poles"}}, "EPSG:26331")
    try:
        QgsSettings().setValue(GLOBAL_KEY, global_map.to_json())
        save_schema_map(project_map, qgis_new_project)

        loaded = load_schema_map(qgis_new_project)

        assert loaded == project_map
        assert json.loads(loaded.to_json())["roles"]["pole"]["layer"] == "Project poles"
    finally:
        QgsSettings().remove(GLOBAL_KEY)


def test_proposal_uses_unambiguous_layer_and_field_hints(
    qgis_new_project: QgsProject,
) -> None:
    qgis_new_project.addMapLayer(
        _layer("DSS Transformers", ["ASSET_ID", "RATED_KVA", "LOAD_KVA", "FEEDER_ID"])
    )
    qgis_new_project.addMapLayer(_layer("Customers", ["CUST_ID", "DSS_ID"]))

    mapping = propose_schema_map(qgis_new_project)

    assert mapping.roles["transformer"]["id_field"] == "ASSET_ID"
    assert mapping.roles["transformer"]["rated_field"] == "RATED_KVA"
    assert mapping.roles["customer"]["transformer_key"] == "DSS_ID"


def test_proposal_skips_ambiguous_role_layers(qgis_new_project: QgsProject) -> None:
    qgis_new_project.addMapLayer(_layer("Primary Poles", ["POLE_ID"]))
    qgis_new_project.addMapLayer(_layer("Secondary Poles", ["POLE_ID"]))

    mapping = propose_schema_map(qgis_new_project)

    assert "pole" not in mapping.roles
