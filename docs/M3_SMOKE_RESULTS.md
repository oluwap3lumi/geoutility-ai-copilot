# Milestone 3 smoke-test results

Date: 2026-11-16  
Environment: Windows, QGIS 3.42.1, bundled Python 3.12.9

## Release checklist

| Checklist item | Status | Evidence |
|---|---|---|
| Validation report matches fixture truth and writes only after approval | Partially verified | Tool tests verify 3 transformer orphans, 2 duplicate-ID features, 1 missing mandatory-ID feature, 1 capacity outlier, HTML/CSV output, and overwrite refusal. Controller safety tests verify OUTPUT rejection. Visible approval flow is not manually verified. |
| Four headline prompts work with Claude and Ollama | Partially verified | FakeProvider composite scenarios and both provider wire adapters pass. No Anthropic key is available. Ollama 0.40.16 is installed but has no local models, so live model quality is unverified. |
| PostGIS-backed layer set | Not verified | No PostGIS connection or test database was supplied. Tools use normal QGIS providers and contain no direct database code. |
| ZIP installs in a clean QGIS profile | Partially verified | Deterministic 39-file ZIP passes integrity, content, exclusion, and reproducibility tests. Interactive **Install from ZIP** in a visible clean profile is not verified. |
| 100k layer stays responsive and cancellation works | Partially verified | Indexed 100,000-point selection passes under the 60-second regression bound with capped model-visible IDs. Network cancellation is tested. Main-thread tool responsiveness requires visible GUI observation. |
| Privacy: no coordinates or sensitive fields sent by default | Verified (automated) | Schema-only snapshots, sensitive-field suppression, capped samples, sanitized audit records, and request fixtures are tested. Live packet inspection is not available without a provider request. |
| All tests and static checks are green | Verified | 93 tests passed; Ruff and `black --check` passed; the final ZIP contains 39 valid runtime files at version 0.3.0. |

## Milestone regression summary

- All five v1 tools are registered; no real MODIFY tool ships.
- OUTPUT/MODIFY policy is enforced outside prompts; read-only mode blocks both.
- Geographic distance fixtures match projected results at the inclusive 50 m boundary.
- Plugin lifecycle passes five automated init/unload cycles.
- Chat HTML is escaped, old tool context is compacted, and audit entries omit raw values.

## External verification still required

1. Enable the final ZIP in a visible clean QGIS profile and inspect Log Messages after two reloads.
2. Run the four demo prompts with a configured Claude key.
3. Install or select a tool-capable Ollama model and repeat the demo prompts.
4. Run all five tools against a representative PostGIS-backed project.
