# GeoUtility AI Copilot

GeoUtility AI Copilot is a QGIS plugin for electricity-distribution GIS teams. It provides a
dock-panel chat where Claude can inspect project layers and invoke bounded GIS tools.

Milestone 1 includes schema-only layer awareness and two executable tools:

- `inspect_layers`: list layers or inspect one vector layer's schema.
- `query_features`: filter with a validated QGIS expression, aggregate, and optionally select.

Selections are reversible and do not edit source data. Output and modification tools are not part
of Milestone 1.

## Development

Use QGIS 3.34 or newer and its bundled Python. This workspace is configured for QGIS 3.42.1 at
`C:\Program Files\QGIS 3.42.1`. Development uses the separate `copilot-dev` QGIS profile.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev_link.ps1
```

The plugin package is `geoutility_copilot/`. No real utility or customer data belongs in this
repository.

## Install for development

1. Create or select the separate QGIS profile `copilot-dev`.
2. Run `scripts\dev_link.ps1` from PowerShell.
3. Launch QGIS with `qgis --profile copilot-dev`.
4. Enable **GeoUtility AI Copilot** under *Plugins → Manage and Install Plugins*.
5. Open **Settings** in the dock and store an Anthropic API key. The key is stored through QGIS
   Authentication Manager; plaintext keys are never written to `QgsSettings` or logs.

## Privacy defaults

- Project snapshots contain layer/schema metadata, CRS, counts, and selection counts.
- Attribute samples are disabled by default.
- Geometry coordinates are not sent.
- Tool audit records contain operational metadata, not prompts, expressions, attributes, or tool
  result data.

## Checks

```powershell
python -m ruff check .
python -m black --check .
python -m pytest -q
```

Use QGIS's bundled Python/environment. See `BUILD_PLAN.md` for milestones and `AGENTS.md` for the
architecture and safety contract.
