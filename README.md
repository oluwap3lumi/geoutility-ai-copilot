# GeoUtility AI Copilot

GeoUtility AI Copilot is a QGIS plugin for electricity-distribution GIS teams. It provides a
dock-panel chat where an LLM can inspect project layers and invoke five bounded GIS tools.

The project is under active development. See `AGENTS.md` for architecture and safety rules and
`BUILD_PLAN.md` for the milestone order.

## Development

Use QGIS 3.34 or newer and its bundled Python. This workspace is configured for QGIS 3.42.1 at
`C:\Program Files\QGIS 3.42.1`. Development uses the separate `copilot-dev` QGIS profile.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev_link.ps1
```

The plugin package is `geoutility_copilot/`. No real utility or customer data belongs in this
repository.
