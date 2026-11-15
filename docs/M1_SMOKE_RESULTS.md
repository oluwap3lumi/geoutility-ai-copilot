# Milestone 1 smoke results — 2026-11-15

- **Verified (automated, headless QGIS):** plugin factory, action/dock toggle, unload, and two reload cycles; pytest-qgis lifecycle tests pass.
- **Verified (automated):** dock input, role rendering, Stop/Clear state, settings persistence, privacy notice, and task cancellation.
- **Verified (fake transport):** rejected API key produces a friendly error without exposing the key; provider failures return safe messages.
- **Verified (automated, empty project):** snapshot and `inspect_layers` return a valid zero-layer result.
- **Verified (real in-memory QGIS layers):** layer names, geometry type, CRS, fields, counts, expression selection, and grouped aggregates are correct.
- **Verified (automated):** malformed expressions and unknown layers/fields return actionable errors.
- **Verified (automated):** Ruff, Black, and pytest pass without live network access.
- **Verified (automated):** audit JSONL records each controller tool call without raw argument values or result data.
- **Not verified:** visible QGIS Log Messages panel after Plugin Reloader reloads; headless lifecycle coverage is the available evidence.
- **Not verified:** real Claude response, UI responsiveness during a real request, wrong live key, and physical network disconnection. No API key was supplied for live testing.
