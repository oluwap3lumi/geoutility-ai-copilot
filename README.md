# GeoUtility AI Copilot

GeoUtility AI Copilot is a QGIS plugin for electricity-distribution GIS teams. It provides a
dock-panel chat where Claude or a local Ollama model can inspect project layers and invoke bounded
GIS tools.

Version 1 includes schema-aware layer context and exactly five executable tools:

- `inspect_layers`: list layers or inspect one vector layer's schema.
- `query_features`: filter with a validated QGIS expression, aggregate, and optionally select.
- `spatial_select`: select by metric distance or exact spatial relationship across differing CRSs.
- `find_unconnected`: find orphan assets by normalized keys or spatial tolerance, optionally adding
  an approved temporary result layer.
- `generate_report`: write an approved HTML validation report with optional CSV findings.

Selections are reversible and do not edit source data. GeoUtility does not ship a source-data
modification tool in v1.

## Development

Use QGIS 3.34 or newer and its bundled Python. This workspace is configured for QGIS 3.42.1 at
`C:\Program Files\QGIS 3.42.1`. Development uses the separate `copilot-dev` QGIS profile.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev_link.ps1
```

The plugin package is `geoutility_copilot/`. No real utility or customer data belongs in this
repository.

## Install

Build the distributable archive with QGIS Python:

```powershell
python scripts/package.py
```

In QGIS, open **Plugins → Manage and Install Plugins → Install from ZIP**, choose
`dist/geoutility_copilot.zip`, then enable **GeoUtility AI Copilot**.

## Install for development

1. Create or select the separate QGIS profile `copilot-dev`.
2. Run `scripts\dev_link.ps1` from PowerShell.
3. Launch QGIS with `qgis --profile copilot-dev`.
4. Enable **GeoUtility AI Copilot** under *Plugins → Manage and Install Plugins*.
5. Open **Settings** in the dock and store an Anthropic API key. The key is stored through QGIS
   Authentication Manager; plaintext keys are never written to `QgsSettings` or logs.

## Providers

### Claude

Choose **Claude**, set the model identifier, and store the Anthropic API key in Settings. Requests
use QGIS networking so configured proxy and SSL behavior is respected.

### Ollama

Choose **Ollama (local)**, set the model and host (default `http://localhost:11434`). The selected
model must support tool calling. GeoUtility does not install or download Ollama models.

## Schema map

The schema map connects semantic utility roles (`transformer`, `customer`, `pole`, and
`feeder_11kv`) to the layer and field names in the current project. Open **Settings**, choose
**Propose from project**, review the editable JSON, and save only after the mapping is correct.
Confirmed mappings are stored in the QGIS project with a global fallback. The copilot exposes
confirmed roles to the model but never silently confirms proposed roles.

## Safety and approvals

- READ operations run automatically and do not change project state.
- SELECTION operations run automatically, appear as tool steps, and include **Undo selection**.
- OUTPUT operations require explicit approval before adding a layer or writing a file.
- **Approve for this chat session** applies only to OUTPUT; it never applies to MODIFY.
- **Read-only mode** blocks OUTPUT and MODIFY completely.
- No real MODIFY tool ships in v1.

`find_unconnected(create_layer=false)` is READ. Setting `create_layer=true` changes that call to
OUTPUT and triggers the approval dialog before the temporary layer is created.

## Privacy defaults

- Project snapshots contain layer/schema metadata, CRS, counts, and selection counts.
- Attribute samples are disabled by default.
- Geometry coordinates are not sent.
- Tool audit records contain operational metadata, not prompts, expressions, attributes, or tool
  result data.

## Troubleshooting and limitations

- **No API key:** Claude requires a key in Settings; Ollama does not.
- **Ollama cannot call tools:** choose a model explicitly advertised with tool support.
- **Layer not found:** review the schema map and ensure mapped layers are loaded.
- **Distance error:** configure a projected metric CRS; geographic layers are transformed.
- **Report already exists:** choose a new filename; reports are never overwritten silently.
- No source attribute or geometry editing tool ships in v1.
- PostGIS still requires release validation against a real deployment.
- Automated tests never call live Claude or Ollama services.

See [the synthetic demo](docs/demo.md) for the headline workflows.

## Checks

```powershell
python -m ruff check .
python -m black --check .
python -m pytest -q
```

Use QGIS's bundled Python/environment. See `BUILD_PLAN.md` for milestones and `AGENTS.md` for the
architecture and safety contract.
