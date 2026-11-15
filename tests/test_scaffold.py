"""Baseline checks for the repository scaffold."""

from __future__ import annotations

import importlib


def test_core_boundaries_import_without_ui_side_effects() -> None:
    modules = (
        "geoutility_copilot",
        "geoutility_copilot.core",
        "geoutility_copilot.core.llm",
        "geoutility_copilot.core.tools",
    )

    for module in modules:
        importlib.import_module(module)
