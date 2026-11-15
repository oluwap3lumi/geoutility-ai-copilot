"""Validate deterministic M2 synthetic fixture data."""

from __future__ import annotations

import json
from pathlib import Path

from qgis.core import QgsVectorLayer

from tests.data.make_fixtures import generate


def test_generator_writes_valid_layers_with_known_counts(tmp_path: Path) -> None:
    gpkg = tmp_path / "network.gpkg"
    truth_path = tmp_path / "expected.json"
    generate(gpkg, truth_path)
    expected = json.loads(truth_path.read_text(encoding="utf-8"))

    for base_name, count in expected["counts"].items():
        for suffix in ("32631", "4326"):
            layer = QgsVectorLayer(f"{gpkg}|layername={base_name}_{suffix}", base_name, "ogr")
            assert layer.isValid()
            assert layer.featureCount() == count


def test_truth_file_is_byte_deterministic(tmp_path: Path) -> None:
    first_gpkg = tmp_path / "first.gpkg"
    second_gpkg = tmp_path / "second.gpkg"
    first_truth = tmp_path / "first.json"
    second_truth = tmp_path / "second.json"

    generate(first_gpkg, first_truth)
    generate(second_gpkg, second_truth)

    assert first_truth.read_bytes() == second_truth.read_bytes()
