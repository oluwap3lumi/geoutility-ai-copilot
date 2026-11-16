"""Distribution archive contents and reproducibility tests."""

from __future__ import annotations

import zipfile
from pathlib import Path

from scripts.package import build_archive


def test_package_contains_runtime_plugin_and_excludes_caches(tmp_path: Path) -> None:
    archive_path = build_archive(tmp_path / "plugin.zip")
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        metadata = archive.read("geoutility_copilot/metadata.txt").decode("utf-8")

    assert "geoutility_copilot/__init__.py" in names
    assert "geoutility_copilot/resources/prompts/system.md" in names
    assert "geoutility_copilot/core/tools/generate_report.py" in names
    assert "version=0.3.2" in metadata
    assert "geoutility_copilot/LICENSE" in names
    assert "geoutility_copilot/resources/icon.png" in names
    assert all("__pycache__" not in name for name in names)
    assert all(not name.endswith((".pyc", "audit.jsonl", ".env")) for name in names)


def test_package_is_byte_reproducible(tmp_path: Path) -> None:
    first = build_archive(tmp_path / "first.zip")
    second = build_archive(tmp_path / "second.zip")

    assert first.read_bytes() == second.read_bytes()
