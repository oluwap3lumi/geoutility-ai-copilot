# BUILD_PLAN.md — GeoUtility AI Copilot v1

Companion to `AGENTS.md`. Three milestones, each ending in something you can open in QGIS and demo. Do them in order. Do not start a milestone until the previous one's exit checklist is green.

| Milestone | Theme | Ships | Tag |
|---|---|---|---|
| **M1** | Foundation: plugin, chat dock, Claude loop, layer awareness | Chat works end to end with 2 tools (`inspect_layers`, `query_features`) | `v0.1.0` |
| **M2** | Spatial power + safety | `spatial_select`, `find_unconnected`, approval gate, schema map, audit log, selection undo | `v0.2.0` |
| **M3** | Report, local model, hardening, release | `generate_report`, Ollama, read-only mode, packaging, docs, demo scenarios | `v0.3.0` |

Suggested pace: M1 ≈ 4–6 days, M2 ≈ 5–7 days, M3 ≈ 4–6 days of focused work.

---

## 0. Dev environment (do once, before M1)

### 0.1 Prerequisites
- QGIS 3.34 LTR or newer (Windows: install via OSGeo4W or the standalone installer; note the install path).
- VS Code with extensions: Python, Pylance, Ruff, Black Formatter, GitHub Copilot/Claude Code (whichever agent you use).
- Git, and a Claude API key (kept out of the repo).

### 0.2 Point VS Code at QGIS's Python
- **Windows (OSGeo4W):** interpreter is typically `C:\OSGeo4W\apps\Python3xx\python.exe`; launch VS Code from the OSGeo4W shell via `C:\OSGeo4W\bin\python-qgis.bat` environment, or add to `.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": "C:/OSGeo4W/apps/Python312/python.exe",
  "python.analysis.extraPaths": [
    "C:/OSGeo4W/apps/qgis-ltr/python",
    "C:/OSGeo4W/apps/qgis-ltr/python/plugins"
  ],
  "terminal.integrated.env.windows": {
    "PYTHONPATH": "C:/OSGeo4W/apps/qgis-ltr/python;C:/OSGeo4W/apps/qgis-ltr/python/plugins",
    "QGIS_PREFIX_PATH": "C:/OSGeo4W/apps/qgis-ltr"
  },
  "ruff.enable": true,
  "[python]": { "editor.defaultFormatter": "ms-python.black-formatter" }
}
```
Adjust paths/versions to your install. **Verify in the QGIS Python console** with `import sys; sys.version` and `QgsApplication.prefixPath()`.
- Optional: install `qgis-stubs` or `PyQt5-stubs` for completions only (never a runtime dependency).

### 0.3 Link the plugin into QGIS for live development
- Windows plugin folder: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
- `scripts/dev_link.ps1` creates a **directory junction/symlink** from that folder to `./geoutility_copilot`, so edits in VS Code are live.
- Install the **Plugin Reloader** and **First Aid** QGIS plugins for fast reload + tracebacks.
- Create a **separate QGIS profile** (`Settings > User Profiles > New Profile`: `copilot-dev`) so experiments never touch your real profile. Launch with `qgis --profile copilot-dev`.

### 0.4 Test tooling
- `pip install pytest pytest-qgis ruff black` into the QGIS Python env (dev only).
- Add synthetic fixture GeoPackage generator `tests/data/make_fixtures.py` (see M2 for contents).
- `.vscode/tasks.json`: tasks for `ruff`, `black --check`, `pytest`, `package`.

### 0.5 Secrets
- API key via QGIS Auth Manager or the plugin settings dialog. For dev tests use env var `ANTHROPIC_API_KEY` only in the optional integration test. Add `.env`, `*.key`, `audit.jsonl` to `.gitignore`.

**Exit:** QGIS opens with the linked plugin folder visible; `pytest` can `import qgis.core` from the VS Code terminal.

---

## Milestone 1 — Foundation (`v0.1.0`)

**Goal:** Type a question in a dock panel; Claude can look at your layers and answer using two real tools. No safety dialogs yet (only READ/SELECTION tools exist).

### M1 tasks (in order)

1. **Plugin skeleton**
   - `metadata.txt` (name, qgisMinimumVersion=3.34, version 0.1.0, author, repository, experimental=True).
   - `__init__.py` with `classFactory`; `plugin.py` with `initGui`/`unload`, toolbar button + Plugins menu entry "GeoUtility AI Copilot" toggling the dock.
   - **Done when:** enable/disable/reload works twice with a clean Log Messages panel.

2. **Dock + chat UI shell**
   - `ui/dock.py`, `chat_view.py`, `input_bar.py`: message list, multiline input, Send/Stop, Clear.
   - Messages rendered with roles (user/assistant/tool-step/error). Fake echo responder first.
   - **Done when:** dock is dockable, remembers visibility, input never freezes UI.

3. **Settings dialog + secrets**
   - Provider (Claude for now), model name, API key (Auth Manager), "Never send sample values" toggle, metric CRS selector (default EPSG:32631).
   - First-run privacy notice (what is and is not sent).
   - **Done when:** settings persist across restarts; key never appears in logs.

4. **Layer awareness**
   - `core/context.py`: snapshot of project layers (name, id, type, CRS, feature count, fields, selection count, provider).
   - Handle: no layers, non-vector layers (listed, flagged), layers with no CRS, >40 layers.
   - **Done when:** `test_context.py` passes and a manual project with 5+ layers produces a correct, compact snapshot.

5. **LLM provider + agent loop**
   - `core/llm/base.py`, `core/llm/claude.py` using `QgsBlockingNetworkRequest` (no SDK). Off-main-thread via `QgsTask`/worker; result back via signals.
   - `core/agent.py`: loop with iteration cap (8), error cap (3), Stop support, neutral message format, provider-side tool-result translation.
   - `FakeProvider` for tests; `test_agent_loop.py` covers: plain answer, one tool call, chained tool calls, tool error recovery, iteration cap, cancel.
   - **Done when:** typing "hello" against the real API returns a reply in the dock without UI freeze; network failure and bad key show friendly errors.

6. **Tool framework + first two tools**
   - `core/tools/base.py`, `registry.py`, JSON-schema argument validation.
   - `inspect_layers` (READ) and `query_features` (SELECTION; expression validation via `QgsExpression`, select modes, aggregates, limit).
   - Tool-step rows in chat; selection previous-state saved (undo wired in M2).
   - **Done when:** "How many features are in each layer?" and "Select transformers where RATED_KVA > 500" both work on a real project, with correct counts verified manually.

7. **Logging + minimal audit**
   - `core/audit.py` writes JSONL entries per tool call (no raw data values).

8. **Docs + tag**
   - `README.md` quick start; `CHANGELOG.md`; tag `v0.1.0`.

### M1 exit checklist (manual smoke test in real QGIS)
- [ ] Plugin installs via dev link, reloads twice, no errors in Log Messages.
- [ ] Dock opens/closes, input responsive while a request is in flight; Stop cancels cleanly.
- [ ] Wrong API key, no internet, and empty project all produce friendly messages.
- [ ] "What layers do I have?" returns accurate names, geometry types, CRS, counts.
- [ ] A bad expression (typo in a field name) returns a helpful error and the model recovers or explains.
- [ ] `pytest` green, no network used; `ruff` + `black --check` clean.
- [ ] Audit log shows each tool call without raw data.

---

## Milestone 2 — Spatial power + safety (`v0.2.0`)

**Goal:** The core utility prompts work: orphan transformers, poles near a feeder, overloaded DSS along a feeder. Anything that creates outputs is gated by approval.

### M2 tasks (in order)

1. **Synthetic fixtures** (`tests/data/make_fixtures.py` → `network.gpkg`)
   - 10 DSS transformers (3 with no customers, 1 with duplicate ID, 1 with null key, 1 overloaded edge case at exactly threshold), 40 customers, 25 poles at known distances from a 11kV feeder line, 2 feeders. Provide a EPSG:4326 copy and a EPSG:32631 copy of each layer to prove reprojection.
   - Known answers documented in the fixture script docstring.

2. **Schema map**
   - `core/schema_map.py` + `resources/schema_map.json`; loader/validator; role resolution helper used by tools.
   - Settings dialog tab: propose a map from layer/field names, user confirms/edits, saved per QGIS project (project custom properties) with global fallback.
   - Expose roles in `inspect_layers` output and snapshot.

3. **Safety layer** (`core/safety.py`, `ui/approval_dialog.py`)
   - Risk tiers, policy matrix, read-only mode switch, "approve for this session" (OUTPUT only), MODIFY never auto-approved.
   - `Tool.preview()` feeds the dialog (tool, plain description, args, layers, estimated count, destination).
   - `test_safety.py`: full matrix (tier × read-only × approve/reject) plus a FakeModifyTool proving MODIFY always prompts.
   - Approval is awaited on the main thread; rejected → structured error back to model.

4. **`spatial_select`** (SELECTION)
   - Relationships: within_distance (metres), intersects, within, contains; reference limited to selected features or expression.
   - Reprojection to configured metric CRS; geographic-CRS guard; spatial index for speed.
   - Tests against fixtures incl. CRS-mismatch and 4326 vs 32631 equivalence (counts must match within tolerance).

5. **`find_unconnected`** (OUTPUT when creating layer)
   - Attribute-key and spatial modes; normalisation options (trim/case); reports null/duplicate/ambiguous key counts.
   - `create_layer=true` creates a memory layer (approval required) named clearly, styled distinctly.
   - Tests: 3 orphan transformers found; null-key and duplicate-key cases reported, not silently dropped.

6. **Selection undo**
   - Previous selection stored per tool step; "Undo selection" button on step row.

7. **Composite prompt validation (the real test)**
   - Without adding new tools, verify the agent can chain `inspect_layers → query_features/spatial_select` for: "overloaded DSS transformers along this 11kV feeder" (one feeder selected), including the ask-back when no feeder is selected.
   - Tune tool descriptions and system prompt until this works reliably; keep a `tests/prompt_scenarios.md` log of prompts, expected tool sequences, and results.

8. **Docs + tag**
   - Update README (schema map guide, safety explanation), CHANGELOG; tag `v0.2.0`.

### M2 exit checklist
- [ ] "Find all transformers without connected customers." → correct count vs fixture truth; offers a result layer; approval dialog appears before layer is added; rejecting leaves the project unchanged.
- [ ] "Select poles within 50 metres of the feeder." → correct count in both 4326 and 32631 projects.
- [ ] "Identify overloaded DSS transformers along this 11kV feeder." → correct selection/summary; asks for a feeder if none is selected.
- [ ] Read-only mode blocks OUTPUT tier with a clear message.
- [ ] Audit log records approval decisions.
- [ ] Layer deleted mid-chat → friendly error, no crash.
- [ ] Tests green; reload twice clean.

---

## Milestone 3 — Report, local model, hardening, release (`v0.3.0`)

**Goal:** Fifth tool shipped, works offline with Ollama, hardened for real analyst use and installable by someone else.

### M3 tasks (in order)

1. **`generate_report`** (OUTPUT)
   - Checks as listed in `AGENTS.md` 5.5, each toggleable; implemented as separate small functions returning `{check, severity, count, sample_ids}`.
   - HTML report (self-contained, simple CSS, summary table first) + optional CSV per check; metadata footer.
   - Output folder chosen via approval dialog; never overwrite without approval.
   - Tests against fixtures with known issue counts per check.

2. **Ollama provider**
   - `core/llm/ollama.py` with `/api/chat` + tools; provider switch in settings; connection test button; clear message when the selected model lacks tool support.
   - Wire-format tests with recorded fixtures; run the same prompt scenarios and document which small models handled them.

3. **Performance and scale**
   - Test with a realistic large layer (e.g., 100k+ points): spatial index use, feature iteration with request limits, `QgsTask` progress + cancel for Processing runs, result caps enforced.
   - Token/context hygiene: truncate old tool results in history, cap snapshot size, show a usage hint.

4. **Hardening**
   - Retry/backoff on 429/5xx; timeouts; clear offline mode.
   - Sanitise everything echoed in the UI (no HTML injection from layer/field names).
   - Confirm `unload()` leaves no signals/tasks; stress reload 5 times.
   - PostGIS check: run all five tools against a PostGIS-backed layer set (via QGIS provider); document quirks (primary keys, case-sensitive fields, `fid`).

5. **UX polish**
   - Chat Markdown-lite rendering, copy button on replies, example-prompt chips on empty state ("Find transformers without customers", "Select poles within 50 m of feeder", etc.), "Open audit log", "Export chat".

6. **Packaging + docs**
   - `scripts/package.py` builds `geoutility_copilot.zip` (excludes tests, dev files); verify install via *Plugins > Install from ZIP* in a clean profile.
   - README: install, API key setup, Ollama setup, schema map, safety model, privacy notes, troubleshooting, limitations.
   - `docs/demo.md`: the four headline prompts as a scripted demo on synthetic data.

7. **Release**
   - Final regression of all milestone checklists; tag `v0.3.0`; optional: prepare for qgis plugin repository submission (metadata, licence, icon, tracker URL).

### M3 exit checklist
- [ ] "Generate a network asset validation report." produces a correct HTML report with counts matching fixture truth, written only after approval.
- [ ] Same four headline prompts work with Claude and with at least one Ollama model (document which).
- [ ] Works on a PostGIS-backed layer set.
- [ ] Zip installs in a **clean** QGIS profile and runs with no console errors.
- [ ] Large-layer test: UI stays responsive; cancel works.
- [ ] Privacy: verified from request logs that no coordinates or sensitive fields are sent by default.
- [ ] All tests green; docs complete; `v0.3.0` tagged.

---

## Risk register

| Risk | Mitigation |
|---|---|
| Wrong distances from degrees | Always reproject to metric CRS; test 4326 vs projected equivalence |
| Model hallucinates layer/field names | Snapshot + `inspect_layers` first; tool errors list valid names; schema map |
| UI freezes / crashes from threading | Network off-thread only; all PyQGIS on main thread; tests for cancel and unload |
| Customer data leaks to a cloud LLM | Schema-only default, sensitive-field flag, Ollama option, first-run notice, audit |
| Unsafe edits | No MODIFY tools in v1; policy enforced in code, not prompt |
| Local models weak at tool calling | Treat Ollama as best-effort; document tested models; keep tool schemas simple |
| API/model name drift | Model name is a setting; verify against Anthropic docs before release |

## Post-v1 backlog (not now)
Attribute-edit tools with edit-buffer + undo, MCP server exposing the tool layer, streaming responses, map-extent awareness, PostGIS-native queries, saved prompt workflows, multi-feeder batch validation, language packs.
