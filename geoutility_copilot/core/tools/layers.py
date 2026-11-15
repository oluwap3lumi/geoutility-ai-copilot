"""Shared safe layer resolution."""

from __future__ import annotations

from qgis.core import QgsProject, QgsVectorLayer


def resolve_vector_layer(project: QgsProject, reference: str) -> QgsVectorLayer:
    """Resolve a vector layer by ID or unique case-insensitive name."""
    by_id = project.mapLayer(reference)
    if by_id is not None:
        if isinstance(by_id, QgsVectorLayer):
            return by_id
        raise ValueError(f"Layer '{reference}' is not a vector layer.")
    matches = [
        layer
        for layer in project.mapLayers().values()
        if layer.name().casefold() == reference.casefold()
    ]
    if len(matches) > 1:
        raise ValueError(
            "Layer name '{}' is ambiguous. Use an ID: {}.".format(
                reference, ", ".join(layer.id() for layer in matches)
            )
        )
    if not matches:
        names = ", ".join(sorted(layer.name() for layer in project.mapLayers().values()))
        raise ValueError("Layer '{}' not found. Available: {}.".format(reference, names or "none"))
    if not isinstance(matches[0], QgsVectorLayer):
        raise ValueError(f"Layer '{reference}' is not a vector layer.")
    return matches[0]
