# Changelog

All notable changes to this project will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases use
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- The fifth v1 tool, `generate_report`, with eight independently selectable utility-network
  validation checks, self-contained HTML, optional CSV findings, metadata, and overwrite refusal.
- Local Ollama `/api/chat` support with neutral tool/message translation, configurable host,
  provider settings, and clear unsupported-model errors.
- A 100,000-feature indexed spatial regression, bounded model-visible results, compacted older
  tool history, and provider token-usage hints in the dock.
- Bounded 429/5xx retries, a 60-second network transfer timeout, inert HTML rendering in chat,
  and five-cycle plugin lifecycle stress coverage.
- Assistant copy controls, example-prompt buttons, New Session, audit-log opening, and
  user-selected plain-text chat export.
- Deterministic runtime-only plugin ZIP packaging, complete provider/setup/troubleshooting
  documentation, and a synthetic-data demo script.

## [0.2.0] - 2026-11-15

### Added

- Deterministic projected/geographic synthetic utility fixtures and machine-readable truth data.
- Project-aware semantic schema maps with validation, conservative proposals, settings editing,
  and role/sensitivity exposure in layer context.
- Code-enforced risk policy, read-only blocking, explicit output/modify approval dialog,
  OUTPUT session approval, and approval-aware audit records.
- CRS-safe `spatial_select` with metre-distance, geometry predicates, selected/expression
  reference filters, spatial indexing, and geographic/projected fixture parity.
- Attribute and spatial `find_unconnected` analysis with normalization diagnostics,
  argument-sensitive approval, and optional temporary orphan result layers.
- One-shot selection undo controls backed by private controller snapshots and safe
  handling when target layers are removed.
- Versioned composite-prompt guidance and deterministic scenarios for orphan assets,
  feeder-distance selection, overloaded transformers, and ambiguous feeder ask-back.

## [0.1.0] - 2026-11-15

### Added

- Initial repository and development-tooling scaffold.
- QGIS plugin metadata, loader entry point, and clean action/dock lifecycle.
- Docked chat shell with role-aware messages, keyboard input, Stop/Clear controls, and saved dock state.
- Persistent provider/privacy/CRS settings and QGIS Auth Manager-backed API-key storage.
- Deterministic, schema-only QGIS project snapshots with privacy and layer-count caps.
- Provider-neutral agent loop, Claude Messages API mapping, cancellable QGIS worker tasks, and live dock controller.
- Strict tool registry with `inspect_layers` and expression-based `query_features` tools.
- Privacy-safe append-only JSONL audit records for every tool call.
