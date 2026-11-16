"""Build a deterministic QGIS plugin ZIP from runtime files only."""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "geoutility_copilot"
DEFAULT_OUTPUT = ROOT / "dist" / "geoutility_copilot.zip"
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
ZIP_TIMESTAMP = (2020, 1, 1, 0, 0, 0)


def build_archive(output: Path = DEFAULT_OUTPUT) -> Path:
    """Write a reproducible archive rooted at the plugin package name."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source in sorted(PLUGIN.rglob("*")):
            if not source.is_file() or _excluded(source):
                continue
            relative = Path(PLUGIN.name) / source.relative_to(PLUGIN)
            info = zipfile.ZipInfo(relative.as_posix(), ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, source.read_bytes(), compresslevel=9)
    return output


def _excluded(path: Path) -> bool:
    return (
        bool(EXCLUDED_PARTS.intersection(path.parts))
        or path.suffix in EXCLUDED_SUFFIXES
        or path.name in {"audit.jsonl", ".env"}
    )


def main() -> int:
    """Build the default distribution archive."""
    build_archive()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
