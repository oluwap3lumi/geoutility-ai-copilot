"""Validated semantic utility roles mapped to project layers and fields."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from qgis.core import QgsProject, QgsSettings, QgsVectorLayer

PROJECT_GROUP = "GeoUtilityCopilot"
PROJECT_KEY = "schemaMap"
GLOBAL_KEY = "GeoUtilityCopilot/schemaMap"

ROLE_LAYER_HINTS = {
    "transformer": ("transformer", "dss"),
    "customer": ("customer", "consumer"),
    "pole": ("pole",),
    "feeder_11kv": ("feeder", "11kv"),
}
ROLE_FIELD_HINTS = {
    "transformer": {
        "id_field": ("transformer_id", "asset_id", "dss_id"),
        "rated_field": ("rated_kva", "capacity_kva", "rating_kva"),
        "load_field": ("load_kva", "demand_kva"),
        "feeder_field": ("feeder_id",),
    },
    "customer": {
        "id_field": ("customer_id", "cust_id"),
        "transformer_key": ("transformer_id", "dss_id"),
    },
    "pole": {"id_field": ("pole_id", "asset_id"), "feeder_field": ("feeder_id",)},
    "feeder_11kv": {"id_field": ("feeder_id", "asset_id")},
}


@dataclass(frozen=True)
class SchemaMap:
    """Confirmed semantic roles and analysis defaults."""

    roles: dict[str, dict[str, Any]]
    metric_crs: str = "EPSG:32631"
    overload_threshold: float = 1.0

    def to_json(self) -> str:
        """Serialize deterministically for project/global persistence."""
        return json.dumps(
            {
                "roles": self.roles,
                "metric_crs": self.metric_crs,
                "overload_threshold": self.overload_threshold,
            },
            separators=(",", ":"),
            sort_keys=True,
        )


def load_schema_map(project: Optional[QgsProject] = None) -> SchemaMap:
    """Load project mapping, then global fallback, then packaged defaults."""
    current = project or QgsProject.instance()
    text, ok = current.readEntry(PROJECT_GROUP, PROJECT_KEY, "")
    if not ok or not text:
        text = QgsSettings().value(GLOBAL_KEY, "", type=str)
    if not text:
        text = _default_path().read_text(encoding="utf-8")
    return parse_schema_map(text)


def parse_schema_map(text: str) -> SchemaMap:
    """Parse and structurally validate schema-map JSON."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Schema map is not valid JSON.") from exc
    roles = data.get("roles")
    if not isinstance(roles, dict):
        raise ValueError("Schema map must contain a 'roles' object.")
    for role, mapping in roles.items():
        if not isinstance(mapping, dict) or not isinstance(mapping.get("layer"), str):
            raise ValueError(f"Role '{role}' must specify a layer name.")
    return SchemaMap(
        roles=roles,
        metric_crs=str(data.get("metric_crs", "EPSG:32631")),
        overload_threshold=float(data.get("overload_threshold", 1.0)),
    )


def validate_schema_map(mapping: SchemaMap, project: QgsProject) -> list[str]:
    """Return actionable layer/field mapping errors."""
    errors = []
    for role, values in mapping.roles.items():
        matches = [
            layer
            for layer in project.mapLayers().values()
            if layer.name().casefold() == str(values["layer"]).casefold()
        ]
        if len(matches) != 1 or not isinstance(matches[0], QgsVectorLayer):
            errors.append(f"Role '{role}' layer '{values['layer']}' was not found uniquely.")
            continue
        available = {field.name().casefold() for field in matches[0].fields()}
        for key, value in values.items():
            if key == "layer":
                continue
            if key == "sensitive_fields":
                for field_name in value:
                    if str(field_name).casefold() not in available:
                        errors.append(f"Role '{role}' field '{field_name}' does not exist.")
                continue
            if (key.endswith("_field") or key.endswith("_key")) and str(
                value
            ).casefold() not in available:
                errors.append(f"Role '{role}' field '{value}' does not exist.")
    return errors


def roles_for_layer(mapping: SchemaMap, layer: QgsVectorLayer) -> list[str]:
    """Return configured roles assigned to a layer by name."""
    name = layer.name().casefold()
    return sorted(
        role
        for role, values in mapping.roles.items()
        if str(values.get("layer", "")).casefold() == name
    )


def sensitive_fields_for_layer(mapping: SchemaMap, layer: QgsVectorLayer) -> set[str]:
    """Return case-folded fields that must never be sampled."""
    sensitive: set[str] = set()
    for role in roles_for_layer(mapping, layer):
        sensitive.update(
            str(name).casefold() for name in mapping.roles[role].get("sensitive_fields", [])
        )
    return sensitive


def propose_schema_map(project: QgsProject, metric_crs: str = "EPSG:32631") -> SchemaMap:
    """Propose editable roles from conservative layer and field name hints."""
    vector_layers = [
        layer for layer in project.mapLayers().values() if isinstance(layer, QgsVectorLayer)
    ]
    roles: dict[str, dict[str, Any]] = {}
    for role, hints in ROLE_LAYER_HINTS.items():
        matches = [
            layer
            for layer in vector_layers
            if any(hint in layer.name().casefold() for hint in hints)
        ]
        if len(matches) != 1:
            continue
        layer = matches[0]
        values: dict[str, Any] = {"layer": layer.name()}
        fields = {field.name().casefold(): field.name() for field in layer.fields()}
        for semantic_name, candidates in ROLE_FIELD_HINTS[role].items():
            match = next((fields[name] for name in candidates if name in fields), None)
            if match:
                values[semantic_name] = match
        roles[role] = values
    return SchemaMap(roles=roles, metric_crs=metric_crs)


def save_schema_map(mapping: SchemaMap, project: Optional[QgsProject] = None) -> None:
    """Persist a confirmed map in the current project and global fallback."""
    current = project or QgsProject.instance()
    text = mapping.to_json()
    current.writeEntry(PROJECT_GROUP, PROJECT_KEY, text)
    QgsSettings().setValue(GLOBAL_KEY, text)


def _default_path() -> Path:
    return Path(__file__).parents[1] / "resources" / "schema_map.json"
