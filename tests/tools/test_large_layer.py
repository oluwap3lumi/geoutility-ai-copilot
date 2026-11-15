"""Scale regression for indexed spatial selection and result caps."""

from __future__ import annotations

from time import perf_counter

from qgis.core import QgsFeature, QgsGeometry, QgsPointXY, QgsProject, QgsVectorLayer

from geoutility_copilot.core.tools.base import ToolContext
from geoutility_copilot.core.tools.spatial_select import SpatialSelectTool


def test_spatial_selection_caps_100k_layer_results(qgis_new_project: QgsProject) -> None:
    points = QgsVectorLayer("Point?crs=EPSG:32631", "large_points", "memory")
    for start in range(0, 100_000, 10_000):
        features = []
        for index in range(start, start + 10_000):
            feature = QgsFeature(points.fields())
            feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(500_000 + index, 0)))
            features.append(feature)
        assert points.dataProvider().addFeatures(features)[0]
    feeder = QgsVectorLayer("LineString?crs=EPSG:32631", "long_feeder", "memory")
    line = QgsFeature(feeder.fields())
    line.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(500_000, 0), QgsPointXY(599_999, 0)]))
    assert feeder.dataProvider().addFeature(line)
    qgis_new_project.addMapLayer(points)
    qgis_new_project.addMapLayer(feeder)

    started = perf_counter()
    result = SpatialSelectTool().run(
        {
            "target_layer": points.id(),
            "reference_layer": feeder.id(),
            "relationship": "within_distance",
            "distance_m": 1,
        },
        ToolContext(qgis_new_project, max_result_ids=20),
    )
    duration = perf_counter() - started

    assert result.ok
    assert result.data["selected_count"] == 100_000
    assert len(result.data["sample_ids"]) == 20
    assert duration < 60
