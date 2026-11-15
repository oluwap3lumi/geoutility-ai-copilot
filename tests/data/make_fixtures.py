"""Generate deterministic synthetic utility layers and their known answers.

Truth: 2 feeders, 10 transformer features, 40 customers, and 25 poles. Transformer
features 8, 9, and 10 have no customers; features 8/9 share ``T08`` and feature 10
has a null ID. Transformer T02 is exactly at its rated capacity. Pole offsets from
F01 include 49 m, 50 m, and 51 m.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QMetaType

DATA_DIR = Path(__file__).parent
GPKG_PATH = DATA_DIR / "network.gpkg"
TRUTH_PATH = DATA_DIR / "expected.json"


def generate(output_path: Path = GPKG_PATH, truth_path: Path = TRUTH_PATH) -> None:
    """Write all fixture layers and deterministic expected values."""
    projected = _projected_layers()
    geographic = [_reproject(layer, "EPSG:4326") for layer in projected]
    for index, layer in enumerate(projected + geographic):
        _write_layer(layer, output_path, overwrite_file=index == 0)
    truth = {
        "counts": {"feeders": 2, "transformers": 10, "customers": 40, "poles": 25},
        "unconnected_transformer_feature_indexes": [8, 9, 10],
        "duplicate_transformer_id": "T08",
        "null_transformer_feature_index": 10,
        "threshold_transformer_id": "T02",
        "pole_offsets_m": [0, 10, 20, 25, 30, 40, 49, 50, 51, 60, 75, 100],
    }
    truth_path.write_text(json.dumps(truth, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _projected_layers() -> list[QgsVectorLayer]:
    return [_feeders(), _transformers(), _customers(), _poles()]


def _feeders() -> QgsVectorLayer:
    layer = _layer("LineString", "feeders_32631", [("feeder_id", QMetaType.Type.QString)])
    _add_rows(
        layer,
        [
            (["F01"], QgsGeometry.fromWkt("LINESTRING(500000 0,501000 0)")),
            (["F02"], QgsGeometry.fromWkt("LINESTRING(500000 1000,501000 1000)")),
        ],
    )
    return layer


def _transformers() -> QgsVectorLayer:
    fields = [
        ("transformer_id", QMetaType.Type.QString),
        ("feeder_id", QMetaType.Type.QString),
        ("rated_kva", QMetaType.Type.Double),
        ("load_kva", QMetaType.Type.Double),
    ]
    layer = _layer("Point", "transformers_32631", fields)
    rows = []
    identifiers = ["T01", "T02", "T03", "T04", "T05", "T06", "T07", "T08", "T08", None]
    for index, identifier in enumerate(identifiers):
        feeder = "F01" if index < 5 else "F02"
        y = 10.0 if index < 5 else 1010.0
        rated = 100.0 + index * 25
        load = rated if identifier == "T02" else rated * (1.2 if identifier == "T06" else 0.8)
        rows.append(
            (
                [identifier, feeder, rated, load],
                QgsGeometry.fromPointXY(_point(500100 + index * 80, y)),
            )
        )
    _add_rows(layer, rows)
    return layer


def _customers() -> QgsVectorLayer:
    fields = [
        ("customer_id", QMetaType.Type.QString),
        ("transformer_id", QMetaType.Type.QString),
        ("name", QMetaType.Type.QString),
    ]
    layer = _layer("Point", "customers_32631", fields)
    counts = [6, 6, 6, 6, 6, 5, 5]
    rows = []
    customer_index = 1
    for transformer_index, count in enumerate(counts, start=1):
        base_x = 500100 + (transformer_index - 1) * 80
        base_y = 10.0 if transformer_index <= 5 else 1010.0
        for offset in range(count):
            customer_id = f"C{customer_index:03d}"
            rows.append(
                (
                    [
                        customer_id,
                        f"T{transformer_index:02d}",
                        f"Synthetic Customer {customer_index:03d}",
                    ],
                    QgsGeometry.fromPointXY(_point(base_x + offset, base_y + offset)),
                )
            )
            customer_index += 1
    _add_rows(layer, rows)
    return layer


def _poles() -> QgsVectorLayer:
    layer = _layer(
        "Point",
        "poles_32631",
        [("pole_id", QMetaType.Type.QString), ("feeder_id", QMetaType.Type.QString)],
    )
    offsets = [0, 10, 20, 25, 30, 40, 49, 50, 51, 60, 75, 100]
    rows = []
    for index in range(25):
        feeder = "F01" if index < 13 else "F02"
        offset = offsets[index % len(offsets)]
        base_y = 0 if feeder == "F01" else 1000
        rows.append(
            (
                [f"P{index + 1:03d}", feeder],
                QgsGeometry.fromPointXY(_point(500050 + index * 30, base_y + offset)),
            )
        )
    _add_rows(layer, rows)
    return layer


def _layer(geometry: str, name: str, fields: list[tuple[str, Any]]) -> QgsVectorLayer:
    layer = QgsVectorLayer(f"{geometry}?crs=EPSG:32631", name, "memory")
    layer.dataProvider().addAttributes(
        [QgsField(field_name, field_type) for field_name, field_type in fields]
    )
    layer.updateFields()
    return layer


def _add_rows(layer: QgsVectorLayer, rows: list[tuple[list[Any], QgsGeometry]]) -> None:
    features = []
    for attributes, geometry in rows:
        feature = QgsFeature(layer.fields())
        feature.setAttributes(attributes)
        feature.setGeometry(geometry)
        features.append(feature)
    if not layer.dataProvider().addFeatures(features)[0]:
        raise RuntimeError(f"Could not add features to {layer.name()}")


def _reproject(layer: QgsVectorLayer, target_auth_id: str) -> QgsVectorLayer:
    target_crs = QgsCoordinateReferenceSystem(target_auth_id)
    result = QgsVectorLayer(
        f"{QgsWkbTypes.displayString(layer.wkbType())}?crs={target_auth_id}",
        layer.name().replace("32631", "4326"),
        "memory",
    )
    result.dataProvider().addAttributes(list(layer.fields()))
    result.updateFields()
    transform = QgsCoordinateTransform(layer.crs(), target_crs, QgsProject.instance())
    features = []
    for source in layer.getFeatures():
        feature = QgsFeature(result.fields())
        feature.setAttributes(source.attributes())
        geometry = QgsGeometry(source.geometry())
        geometry.transform(transform)
        feature.setGeometry(geometry)
        features.append(feature)
    result.dataProvider().addFeatures(features)
    return result


def _write_layer(layer: QgsVectorLayer, path: Path, overwrite_file: bool) -> None:
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = layer.name()
    options.actionOnExistingFile = (
        QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteFile
        if overwrite_file
        else QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteLayer
    )
    error, message, _, _ = QgsVectorFileWriter.writeAsVectorFormatV3(
        layer, str(path), QgsProject.instance().transformContext(), options
    )
    if error != QgsVectorFileWriter.WriterError.NoError:
        raise RuntimeError(f"Could not write {layer.name()}: {message}")


def _point(x: float, y: float) -> Any:
    return QgsPointXY(x, y)


if __name__ == "__main__":
    generate()
