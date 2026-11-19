"""QGIS-owned expression validation and feature-request context."""

from __future__ import annotations

from typing import Union

from qgis.core import QgsExpression, QgsFeatureRequest, QgsVectorLayer


def expression_request(
    layer: QgsVectorLayer, text: str
) -> Union[QgsFeatureRequest, str]:  # noqa: UP007 - QGIS 3.34 supports Python 3.9
    """Prepare a filter against its layer, returning a request or an actionable error."""
    expression = QgsExpression(text)
    if expression.hasParserError():
        return f"Invalid QGIS expression: {expression.parserErrorString()}"
    context = layer.createExpressionContext()
    # QGIS owns case-insensitive field resolution and dynamic attribute expressions;
    # referencedColumns() may contain AllAttributes, which is not a field name.
    if not expression.prepare(context):
        fields = ", ".join(sorted(field.name() for field in layer.fields())) or "none"
        return (
            f"Invalid QGIS expression: {expression.evalErrorString()} Available fields: {fields}."
        )
    return QgsFeatureRequest(expression).setExpressionContext(context)
