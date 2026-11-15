"""Self-contained network asset validation report generation."""

from __future__ import annotations

import csv
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any, Callable, ClassVar, Optional

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsGeometry,
    QgsProject,
    QgsVariantUtils,
    QgsVectorLayer,
)

from geoutility_copilot.core.schema_map import SchemaMap, load_schema_map, validate_schema_map
from geoutility_copilot.core.tools.base import Risk, ToolContext, ToolResult
from geoutility_copilot.core.tools.layers import resolve_vector_layer

CHECK_NAMES = (
    "invalid_geometry",
    "duplicate_asset_ids",
    "missing_mandatory_attributes",
    "transformers_without_customers",
    "customers_without_transformers",
    "assets_outside_feeder_buffer",
    "crs_inconsistencies",
    "rated_capacity_outliers",
)


@dataclass(frozen=True)
class Finding:
    """One bounded validation result."""

    check: str
    severity: str
    count: int
    sample_ids: tuple[str, ...] = ()


class GenerateReportTool:
    """Run mapped utility checks and write approved report artifacts."""

    name = "generate_report"
    description = (
        "Generate an HTML network asset validation report from confirmed schema-map roles. "
        "Use only when the user requests a written report; this always requires output approval."
    )
    risk = Risk.OUTPUT
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "output_folder": {"type": "string", "maxLength": 1000},
            "report_name": {"type": "string", "maxLength": 200},
            "checks": {"type": "array"},
            "include_csv": {"type": "boolean"},
            "feeder_buffer_m": {"type": "number", "minimum": 0},
        },
        "required": ["output_folder"],
        "additionalProperties": False,
    }

    def preview(self, args: dict[str, Any], context: ToolContext) -> str:
        """Describe the report destination and enabled checks."""
        checks = args.get("checks") or list(CHECK_NAMES)
        return "Write network validation HTML{} to '{}' using checks: {}.".format(
            " and CSV files" if args.get("include_csv") else "",
            args.get("output_folder", "?"),
            ", ".join(str(item) for item in checks),
        )

    def run(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        """Validate mapped layers and write non-overwriting report files."""
        destination = Path(str(args["output_folder"])).expanduser().resolve()
        if not destination.is_dir():
            return ToolResult(False, "Invalid output folder.", error="Output folder must exist.")
        name = str(args.get("report_name") or _default_name())
        if Path(name).name != name or not name.lower().endswith(".html"):
            return ToolResult(
                False, "Invalid report name.", error="Report name must be a plain .html filename."
            )
        enabled = _enabled_checks(args.get("checks"))
        if isinstance(enabled, str):
            return ToolResult(False, "Invalid report checks.", error=enabled)
        html_path = destination / name
        csv_paths = [destination / f"{html_path.stem}-{check}.csv" for check in enabled]
        planned = [html_path, *(csv_paths if args.get("include_csv") else [])]
        collision = next((path for path in planned if path.exists()), None)
        if collision:
            return ToolResult(
                False, "Output already exists.", error=f"Refusing to overwrite '{collision}'."
            )
        mapping = load_schema_map(context.project)
        errors = validate_schema_map(mapping, context.project)
        if errors:
            return ToolResult(False, "Schema map is invalid.", error=" ".join(errors))
        layers = _mapped_layers(mapping, context.project)
        findings = _run_checks(
            enabled, mapping, layers, context, float(args.get("feeder_buffer_m", 50))
        )
        html_path.write_text(_render_html(findings, mapping, layers, context), encoding="utf-8")
        artifacts = [str(html_path)]
        if args.get("include_csv"):
            for finding, path in zip(findings, csv_paths):
                _write_csv(path, finding)
                artifacts.append(str(path))
        counts = {finding.check: finding.count for finding in findings}
        return ToolResult(
            True,
            f"Wrote validation report with {sum(counts.values())} findings.",
            {"report_path": str(html_path), "check_counts": counts, "artifacts": artifacts},
        )


def _enabled_checks(value: Any) -> list[str] | str:
    if value is None:
        return list(CHECK_NAMES)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return "checks must be an array of check names."
    unknown = sorted(set(value) - set(CHECK_NAMES))
    return f"Unknown checks: {', '.join(unknown)}." if unknown else list(dict.fromkeys(value))


def _mapped_layers(mapping: SchemaMap, project: QgsProject) -> dict[str, QgsVectorLayer]:
    return {
        role: resolve_vector_layer(project, str(values["layer"]))
        for role, values in mapping.roles.items()
    }


def _run_checks(
    enabled: list[str],
    mapping: SchemaMap,
    layers: dict[str, QgsVectorLayer],
    context: ToolContext,
    feeder_buffer: float,
) -> list[Finding]:
    checks: dict[str, Callable[[], Finding]] = {
        "invalid_geometry": lambda: _invalid_geometry(layers),
        "duplicate_asset_ids": lambda: _duplicate_ids(mapping, layers),
        "missing_mandatory_attributes": lambda: _missing_attributes(mapping, layers),
        "transformers_without_customers": lambda: _relationship_orphans(mapping, layers, True),
        "customers_without_transformers": lambda: _relationship_orphans(mapping, layers, False),
        "assets_outside_feeder_buffer": lambda: _outside_feeders(layers, context, feeder_buffer),
        "crs_inconsistencies": lambda: _crs_inconsistencies(layers),
        "rated_capacity_outliers": lambda: _capacity_outliers(mapping, layers),
    }
    return [checks[name]() for name in enabled]


def _invalid_geometry(layers: dict[str, QgsVectorLayer]) -> Finding:
    ids = [
        f"{role}:{feature.id()}"
        for role, layer in layers.items()
        for feature in layer.getFeatures()
        if not feature.hasGeometry()
        or feature.geometry().isNull()
        or not feature.geometry().isGeosValid()
    ]
    return _finding("invalid_geometry", ids)


def _duplicate_ids(mapping: SchemaMap, layers: dict[str, QgsVectorLayer]) -> Finding:
    ids: list[str] = []
    for role, values in mapping.roles.items():
        field = values.get("id_field")
        if not field:
            continue
        rows = [
            (feature.id(), _text(feature[str(field)])) for feature in layers[role].getFeatures()
        ]
        counts = Counter(value for _, value in rows if value is not None)
        ids.extend(
            f"{role}:{feature_id}" for feature_id, value in rows if value and counts[value] > 1
        )
    return _finding("duplicate_asset_ids", ids)


def _missing_attributes(mapping: SchemaMap, layers: dict[str, QgsVectorLayer]) -> Finding:
    ids: list[str] = []
    for role, values in mapping.roles.items():
        fields = [
            str(value)
            for key, value in values.items()
            if key == "id_field" or key == "feeder_field"
        ]
        for feature in layers[role].getFeatures():
            if any(_text(feature[field]) is None for field in fields):
                ids.append(f"{role}:{feature.id()}")
    return _finding("missing_mandatory_attributes", ids)


def _relationship_orphans(
    mapping: SchemaMap, layers: dict[str, QgsVectorLayer], transformers_first: bool
) -> Finding:
    transformer = mapping.roles["transformer"]
    customer = mapping.roles["customer"]
    transformer_values = {
        _text(feature[str(transformer["id_field"])])
        for feature in layers["transformer"].getFeatures()
    }
    customer_values = {
        _text(feature[str(customer["transformer_key"])])
        for feature in layers["customer"].getFeatures()
    }
    role = "transformer" if transformers_first else "customer"
    field = str(transformer["id_field"] if transformers_first else customer["transformer_key"])
    valid = customer_values if transformers_first else transformer_values
    ids = [
        f"{role}:{feature.id()}"
        for feature in layers[role].getFeatures()
        if (_text(feature[field]) is None or _text(feature[field]) not in valid)
    ]
    name = (
        "transformers_without_customers" if transformers_first else "customers_without_transformers"
    )
    return _finding(name, ids)


def _outside_feeders(
    layers: dict[str, QgsVectorLayer], context: ToolContext, distance: float
) -> Finding:
    feeder = layers["feeder_11kv"]
    metric = QgsCoordinateReferenceSystem(context.metric_crs)
    feeder_transform = QgsCoordinateTransform(feeder.crs(), metric, context.project)
    feeder_geometries = []
    for feature in feeder.getFeatures():
        geometry = QgsGeometry(feature.geometry())
        geometry.transform(feeder_transform)
        feeder_geometries.append(geometry)
    ids: list[str] = []
    for role in ("transformer", "pole"):
        layer = layers.get(role)
        if layer is None:
            continue
        transform = QgsCoordinateTransform(layer.crs(), metric, context.project)
        for feature in layer.getFeatures():
            geometry = QgsGeometry(feature.geometry())
            geometry.transform(transform)
            if (
                not feeder_geometries
                or min(geometry.distance(item) for item in feeder_geometries) > distance + 0.01
            ):
                ids.append(f"{role}:{feature.id()}")
    return _finding("assets_outside_feeder_buffer", ids)


def _crs_inconsistencies(layers: dict[str, QgsVectorLayer]) -> Finding:
    counts = Counter(layer.crs().authid() or "unknown" for layer in layers.values())
    expected = counts.most_common(1)[0][0] if counts else "unknown"
    ids = [
        role for role, layer in layers.items() if (layer.crs().authid() or "unknown") != expected
    ]
    return _finding("crs_inconsistencies", ids)


def _capacity_outliers(mapping: SchemaMap, layers: dict[str, QgsVectorLayer]) -> Finding:
    values = mapping.roles["transformer"]
    rated = str(values["rated_field"])
    load = str(values["load_field"])
    ids = []
    for feature in layers["transformer"].getFeatures():
        try:
            if float(feature[load]) > float(feature[rated]) * mapping.overload_threshold:
                ids.append(f"transformer:{feature.id()}")
        except (TypeError, ValueError):
            continue
    return _finding("rated_capacity_outliers", ids, "warning")


def _finding(name: str, ids: Iterable[str], severity: str = "error") -> Finding:
    values = tuple(ids)
    return Finding(name, severity, len(values), values[:20])


def _text(value: Any) -> Optional[str]:
    if value is None or QgsVariantUtils.isNull(value):
        return None
    text = str(value).strip()
    return text.casefold() if text else None


def _render_html(
    findings: list[Finding],
    mapping: SchemaMap,
    layers: dict[str, QgsVectorLayer],
    context: ToolContext,
) -> str:
    rows = "".join(
        f"<tr><td>{escape(item.check)}</td><td>{escape(item.severity)}</td><td>{item.count}</td>"
        f"<td>{escape(', '.join(item.sample_ids))}</td></tr>"
        for item in findings
    )
    layer_rows = "".join(
        f"<li>{escape(role)}: {escape(layer.name())} ({escape(layer.crs().authid() or 'unknown')})</li>"
        for role, layer in sorted(layers.items())
    )
    timestamp = datetime.now(timezone.utc).isoformat()
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Network asset validation</title>
<style>body{{font-family:sans-serif;max-width:1100px;margin:2rem auto}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #bbb;padding:.4rem;text-align:left}}th{{background:#eee}}</style></head>
<body><h1>Network asset validation</h1><table><thead><tr><th>Check</th><th>Severity</th><th>Count</th><th>Sample IDs</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Run metadata</h2><ul><li>Timestamp: {escape(timestamp)}</li><li>QGIS: {escape(Qgis.QGIS_VERSION)}</li><li>Model: {escape(context.model)}</li><li>Metric CRS: {escape(mapping.metric_crs)}</li>{layer_rows}</ul></body></html>"""


def _write_csv(path: Path, finding: Finding) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["check", "severity", "count", "sample_id"])
        if finding.sample_ids:
            for sample_id in finding.sample_ids:
                writer.writerow([finding.check, finding.severity, finding.count, sample_id])
        else:
            writer.writerow([finding.check, finding.severity, finding.count, ""])


def _default_name() -> str:
    return datetime.now(timezone.utc).strftime("geoutility-validation-%Y%m%dT%H%M%SZ.html")
