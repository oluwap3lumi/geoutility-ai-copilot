# Milestone 2 smoke-test results

Date: 2026-11-15  
Environment: Windows, QGIS 3.42.1, bundled Python 3.12.9, offscreen automated tests

| Checklist item | Status | Evidence |
|---|---|---|
| Find transformers without customers; correct count; approval before result layer; rejection unchanged | Partially verified | Synthetic fixture returns 3; automated controller test proves rejected OUTPUT adds no layer; approved direct tool test creates a 3-feature memory layer. Visible dialog interaction and live Claude phrasing not verified. |
| Select poles within 50 metres in EPSG:4326 and EPSG:32631 | Verified (automated) | Both fixture copies select 9 poles for F01, including the 50 m boundary. |
| Identify overloaded DSS along this feeder and ask back when ambiguous | Partially verified | FakeProvider chain verifies `inspect_layers` → `spatial_select` → intersecting `query_features`; ask-back executes no tool. Live Claude reliability not verified. |
| Read-only mode blocks OUTPUT clearly | Verified (automated) | Full safety-policy tests cover OUTPUT/MODIFY under read-only mode. |
| Audit log records approval decisions | Verified (automated) | Tests cover automatic, approved/rejected metadata and absence of raw result values. |
| Layer deleted mid-chat gives friendly error | Verified (automated) | Selection undo reports that the target layer was removed without crashing. Tool resolution also returns available layer names. |
| Tests, Ruff, and Black are green | Verified | 75 tests passed; Ruff and `black --check` passed in the QGIS Python environment. |
| Plugin reloads twice cleanly in visible QGIS | Not verified | Requires interactive QGIS Log Messages inspection. M1 offscreen lifecycle tests remain green. |

## Known limitations

- No live Anthropic request was made because no API key was used by automated tests.
- Visible approval-dialog layout and Plugin Reloader behavior require a real QGIS GUI session.
- The fixture validates GeoPackage and memory layers; PostGIS validation remains scheduled for M3.
