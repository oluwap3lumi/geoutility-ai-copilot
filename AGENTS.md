# AGENTS.md — GeoUtility AI Copilot

> Read this file fully before writing or changing any code. It is the source of truth for architecture, conventions and safety rules. If a request conflicts with this file, stop and ask. Companion file: `BUILD_PLAN.md` (milestones and task order).

---

## 1. Project summary

**GeoUtility AI Copilot** is a QGIS plugin that lets GIS analysts (primarily electricity-distribution network teams) operate QGIS through natural language.

- UI: a **dock panel with a chat interface** inside QGIS.
- Brain: an LLM (**Claude API** by default, **Ollama** as local/offline option) using **tool calling**.
- Hands: a small set of **executable GIS tools** built on PyQGIS and QGIS Processing.
- Safety: the model can inspect and analyse freely, but **anything that modifies data or writes outputs needs explicit user approval**.

Example prompts the finished v1 must handle:

1. "Find all transformers without connected customers."
2. "Identify overloaded DSS transformers along this 11kV feeder."
3. "Select poles within 50 metres of the feeder."
4. "Generate a network asset validation report."

### v1 scope (locked)

- QGIS dock panel + chat UI
- Layer awareness (project layers, fields, CRS, counts, selection state)
- **Exactly five executable tools** (section 5)
- Approval gate for anything beyond read-only/selection
- Claude provider (default) + Ollama provider (M3)
- Audit log of every tool call

### Out of scope for v1 (do not build, do not scaffold)

- Editing geometry or attributes in place (the safety tier exists and is unit-tested with a fake tool, but no real MODIFY tool ships)
- Autonomous multi-hour agents, scheduled jobs, web UI, mobile
- Fine-tuning, RAG over documents, vector DBs
- MCP server packaging (design the tool layer so it can be exposed over MCP later; do not build it now)

---

## 2. Tech stack and constraints

| Area | Choice |
|---|---|
| Language | Python 3.9+ (match the QGIS LTR's bundled Python; check `sys.version` inside QGIS) |
| Host | QGIS 3.34 LTR minimum, target current LTR. QGIS 4/Qt6 readiness: use `qgis.PyQt` imports only, never `PyQt5` directly |
| UI | `qgis.PyQt` (QDockWidget, QTextBrowser/QListView for chat, QDialog for approvals) |
| GIS | PyQGIS (`qgis.core`, `qgis.gui`), `processing` / QGIS Processing algorithms (`native:*`) |
| LLM | Anthropic Messages API with tool use; Ollama `/api/chat` with tools |
| Data | Any QGIS-readable source; PostgreSQL/PostGIS layers work through the normal QGIS provider. No direct DB code in v1 except via QGIS layers |
| Config | `QgsSettings` for user prefs, QGIS Auth Manager for API keys, YAML schema map for asset roles |
| Tests | `pytest` + `pytest-qgis` (or QGIS Python env with `qgis_testing`) |
| Lint/format | `ruff`, `black` (line length 100), type hints on all public functions |

### Hard constraints

1. **No heavy third-party dependencies.** QGIS ships its own Python; users cannot be asked to `pip install` into it. Allowed: stdlib, PyQGIS, PyYAML only if already bundled (otherwise parse a JSON schema map instead). **Do not depend on the `anthropic` SDK.** Use `QgsBlockingNetworkRequest` / `QgsNetworkAccessManager` so QGIS proxy settings and SSL config are respected.
2. **Threading rule (critical):** PyQGIS layer and project objects are **not thread-safe**. Tools execute on the **main thread only**. Network calls to the LLM run off the main thread (`QgsTask` or worker `QThread`) and communicate with the UI via Qt signals. Never touch `QgsVectorLayer`, `QgsProject` or widgets from a worker thread.
3. **Never block the UI.** Long Processing runs use `QgsTask`/feedback with a cancel path.
4. **Never send raw feature data to the LLM by default.** Send schema, counts, CRS, and small capped samples only (see section 7).
5. **Distances in metres require a projected CRS.** Never buffer or measure in EPSG:4326 degrees. Reproject to the configured metric CRS (default: UTM zone 31N, EPSG:32631; Nigeria West Belt EPSG:26331 selectable) or use ellipsoidal measurement where the algorithm supports it.

---

## 3. Repository layout

```
geoutility-ai-copilot/
├── AGENTS.md
├── BUILD_PLAN.md
├── README.md
├── pyproject.toml            # ruff, black, pytest config only (not a runtime package)
├── .vscode/
│   ├── settings.json
│   ├── launch.json
│   └── tasks.json
├── scripts/
│   ├── dev_link.ps1          # symlink plugin into QGIS profile (Windows)
│   ├── dev_link.sh           # same for Linux/macOS
│   └── package.py            # builds the distributable zip
├── geoutility_copilot/       # <-- the actual QGIS plugin
│   ├── __init__.py           # classFactory(iface)
│   ├── metadata.txt
│   ├── plugin.py             # GeoUtilityCopilotPlugin: init/unload, toolbar action, dock
│   ├── resources/            # icons, default schema_map.json, prompt templates
│   ├── ui/
│   │   ├── dock.py           # CopilotDock (QDockWidget)
│   │   ├── chat_view.py      # message rendering (user, assistant, tool-step, error)
│   │   ├── input_bar.py      # prompt box, send/stop buttons
│   │   ├── approval_dialog.py
│   │   └── settings_dialog.py
│   ├── core/
│   │   ├── agent.py          # the tool-use loop (provider-agnostic)
│   │   ├── context.py        # builds the layer-awareness snapshot
│   │   ├── safety.py         # risk tiers, approval policy
│   │   ├── audit.py          # append-only JSONL audit log
│   │   ├── schema_map.py     # semantic roles -> layer/field names
│   │   ├── errors.py         # typed exceptions
│   │   ├── llm/
│   │   │   ├── base.py       # LLMProvider ABC, Message/ToolCall dataclasses
│   │   │   ├── claude.py     # Anthropic Messages API client
│   │   │   └── ollama.py     # Ollama client (M3)
│   │   └── tools/
│   │       ├── base.py       # Tool ABC, ToolResult, JSON-schema helpers
│   │       ├── registry.py   # register/lookup/export tool specs
│   │       ├── inspect_layers.py
│   │       ├── query_features.py
│   │       ├── spatial_select.py
│   │       ├── find_unconnected.py
│   │       └── generate_report.py
│   └── i18n/                 # (empty for v1)
└── tests/
    ├── conftest.py
    ├── data/                 # tiny synthetic GeoPackage fixtures (no real customer data)
    ├── test_context.py
    ├── test_agent_loop.py    # uses a FakeProvider, no network
    ├── test_safety.py
    └── tools/test_*.py       # one file per tool
```

**Rule:** `core/` must stay free of `ui/` imports. `ui/` may import `core/`. This keeps the agent and tools testable headless and reusable behind MCP later.

---

## 4. Architecture

```
┌──────────────────────── QGIS main thread ────────────────────────┐
│  CopilotDock (chat UI)                                           │
│     │ user prompt                         ▲ rendered messages    │
│     ▼                                     │                      │
│  AgentController ──► context.snapshot()   │                      │
│     │                                     │                      │
│     │  signal: request_llm(messages,tools)│                      │
│     ▼                                     │                      │
│  ┌────────────── worker thread / QgsTask ───────────┐            │
│  │ LLMProvider.complete(messages, tools) -> reply   │            │
│  └──────────────────────────────────────────────────┘            │
│     │ signal: reply (text and/or tool_calls)                     │
│     ▼                                                            │
│  for each tool_call:                                             │
│     safety.check(tool, args) ─► approval_dialog (if needed)      │
│     tool.run(args) on MAIN thread ─► ToolResult                  │
│     audit.log(...)                                               │
│  append tool_result to messages ─► loop until no tool_calls      │
└──────────────────────────────────────────────────────────────────┘
```

### The agent loop (`core/agent.py`)

1. Build system prompt (section 7) + layer snapshot + conversation history.
2. Call provider with the tool specs from the registry.
3. If the reply contains tool calls: validate args against the tool's JSON schema, run the safety check, execute, append results, go to 2.
4. If the reply is plain text: show it, stop.
5. **Hard limits:** max 8 tool-call iterations per user turn, max 3 consecutive tool errors, user-visible Stop button that cancels at the next safe point. On limit, stop and tell the user why.
6. Tool errors are returned to the model as structured `ToolResult(ok=False, error=...)` so it can recover or explain. They are never swallowed.

### Provider abstraction (`core/llm/base.py`)

```python
@dataclass
class ToolCall:   id: str; name: str; arguments: dict
@dataclass
class LLMReply:   text: str; tool_calls: list[ToolCall]; stop_reason: str; usage: dict

class LLMProvider(ABC):
    @abstractmethod
    def complete(self, system: str, messages: list[dict], tools: list[dict]) -> LLMReply: ...
```

- **Claude:** POST `https://api.anthropic.com/v1/messages` with headers `x-api-key`, `anthropic-version: 2023-06-01`, `content-type: application/json`. Tools use `name`, `description`, `input_schema`. Loop continues while `stop_reason == "tool_use"`; reply with a user message containing `tool_result` blocks keyed by `tool_use_id`. Model name is a **setting** (default: `claude-sonnet-5-5`; verify the current model string against Anthropic docs before release and never hard-code it elsewhere).
- **Ollama:** POST `{host}/api/chat` with `tools`; only models that support tool calling work (document this in the settings dialog). Default host `http://localhost:11434`.
- Keep an internal neutral message format; each provider translates to/from its wire format. Tool-result translation lives in the provider, not the agent.

---

## 5. The five v1 tools

Every tool is a class in `core/tools/` implementing `Tool`:

```python
class Tool(ABC):
    name: str                 # snake_case, stable (it is part of the model contract)
    description: str          # written FOR THE MODEL: when to use, what it returns
    input_schema: dict        # JSON Schema; additionalProperties: false
    risk: Risk                # READ | SELECTION | OUTPUT | MODIFY
    def run(self, args: dict, ctx: ToolContext) -> ToolResult: ...
    def preview(self, args: dict, ctx: ToolContext) -> str:  # human-readable "what will happen"
```

`ToolResult` = `{ok: bool, summary: str, data: dict (capped), artifacts: list[Artifact], error: str|None}`. `data` is what the model sees: **keep it small** (counts, ids, short samples, never full tables).

### 5.1 `inspect_layers` — risk: READ
Return layers in the project (or one named layer): name, id, geometry type, CRS, feature count, fields (name, type), selected count, data provider (gpkg/postgres/shp/memory), and any schema-map role assigned. Optional `include_samples` (max 3 rows, truncated values). This is the model's eyes; it should call this first when unsure.

### 5.2 `query_features` — risk: SELECTION
Filter a layer with a **QGIS expression** (validated with `QgsExpression` before use) and optionally: `select` (set layer selection, modes: new/add/remove/intersect), `aggregate` (count/sum/min/max/mean of a field, optional group-by field), `limit`. Returns count, aggregates, up to N sample ids. Powers "overloaded DSS transformers" (e.g. expression comparing load to rated capacity using schema-map field names). Changes only the selection state, not data.

### 5.3 `spatial_select` — risk: SELECTION
Select features in `target_layer` by spatial relationship to `reference_layer` (optionally only the reference features currently selected or matching an expression): `within_distance` (metres), `intersects`, `within`, `contains`. Implementation: `native:selectbylocation`/`native:extractwithindistance` or `QgsSpatialIndex` + reprojected geometries. Handles CRS mismatch and geographic CRS by reprojecting to the configured metric CRS. Returns selected count and sample ids. Powers "poles within 50 m of the feeder" and "transformers along this 11kV feeder".

### 5.4 `find_unconnected` — risk: OUTPUT (when it creates a result layer) / READ (count only)
Find features in `asset_layer` with **no related features** in `related_layer`, via either `attribute_key` (e.g. transformer ID ↔ customer's transformer ID) or `spatial` (within tolerance metres). Returns count + sample ids; with `create_layer=true` adds a **temporary memory layer** of the orphans to the project (requires approval). Powers "transformers without connected customers". Must handle null keys, whitespace/case mismatches (configurable normalisation) and duplicate keys, and report how many were affected by those edge cases.

### 5.5 `generate_report` — risk: OUTPUT
Run a **network asset validation** over layers mapped in the schema map and write an HTML report (+ optional CSV per check) to a user-approved folder. Checks (each independently toggleable): null/empty/invalid geometry, duplicate asset IDs, missing mandatory attributes, transformers with no customers, customers with no transformer, assets outside the feeder buffer, CRS inconsistencies, rated capacity outliers. Report contains: summary table, per-check findings with counts and sample ids, run metadata (QGIS version, layers, CRS, timestamp, model used). Returns the file path and per-check counts. Never overwrites an existing file without approval.

### Tool design rules

- Tool descriptions say **when to use** and **when not to**. Poor descriptions are the #1 cause of bad tool selection.
- Validate **all** arguments; reject unknown layer names with a message listing valid names (so the model can self-correct). Resolve layers by name or id, case-insensitive, and report ambiguity instead of guessing.
- Never use `eval`/`exec` on model output. Expressions go through `QgsExpression` only. No arbitrary Python execution tool. No shell access. No file access outside approved output folders.
- Every tool must have a `preview()` so the approval dialog can show exactly what will happen.

---

## 6. Safety model

| Tier | Meaning | Examples | Policy |
|---|---|---|---|
| `READ` | No state change | `inspect_layers`, count-only queries | Auto-run |
| `SELECTION` | Changes selection state only (reversible) | `query_features(select=true)`, `spatial_select` | Auto-run, shown in chat; "Undo selection" affordance (store previous selection) |
| `OUTPUT` | Adds layers to the project or writes files | `find_unconnected(create_layer)`, `generate_report` | **Approval required**, dialog shows `preview()` + destination |
| `MODIFY` | Edits source data (attributes/geometry/DB) | *(none ship in v1)* | **Approval required every time**, never "always allow"; layer must be in edit mode; one undo-able edit command. Exists and is unit-tested using a fake tool so v1.1 can add real ones safely |

Rules:
- The approval policy lives in `core/safety.py` and is enforced **in code, outside the prompt**. Telling the model "ask first" is not a control.
- Approval dialog shows: tool name, plain-language description, arguments, affected layer(s), estimated feature count, destination path. Buttons: **Approve**, **Reject**, and for OUTPUT only, **Approve for this chat session**.
- A rejected call returns `ToolResult(ok=False, error="User rejected")` to the model.
- Provide a settings switch "Read-only mode" that blocks OUTPUT and MODIFY tiers entirely.
- Never edit a layer that is not already user-editable; never toggle edit mode silently.

### Privacy
- Default payload to the LLM: schema, counts, CRS, selection counts, capped samples (max 3 rows, each value truncated to 40 chars). No geometry coordinates, no customer names/phones/addresses.
- Settings toggle "Never send sample values" (schema only).
- Fields flagged `sensitive` in the schema map are never sampled.
- Show a first-run notice explaining what leaves the machine; recommend Ollama for sensitive data.
- API key stored via **QGIS Auth Manager** (fallback: `QgsSettings`, documented as less secure). Never log keys. Never put keys in repo, tests or fixtures.

### Audit log
Append-only JSONL at the QGIS profile dir (`geoutility_copilot/audit.jsonl`): timestamp, user turn id, tool, args, risk tier, approval decision, result summary, duration. No raw data values. Provide "Open audit log" in the dock menu.

---

## 7. Layer awareness and prompting

### Layer snapshot (`core/context.py`)
Generated at the start of each user turn and after any tool that changes the project. Compact, deterministic text/JSON:

```
project_crs: EPSG:32631 | metric_crs_setting: EPSG:32631
layers:
  - name: "DSS Transformers" id: dss_xxx type: Point crs: EPSG:4326 features: 2,431 selected: 0
    fields: ASSET_ID(str), RATED_KVA(int), LOAD_KVA(double), FEEDER_ID(str), STATUS(str)
    role: transformer
  - name: "11kV Feeders" ...
```
Cap at ~40 layers; if more, list names only and let `inspect_layers` fetch detail. Include active layer and map extent only as a hint.

### Schema map (`core/schema_map.py`, `resources/schema_map.json`)
User-editable mapping of **semantic roles** to real layer and field names, so prompts work across differently-named datasets:

```json
{
  "roles": {
    "transformer": {"layer": "DSS Transformers", "id_field": "ASSET_ID", "rated_field": "RATED_KVA", "load_field": "LOAD_KVA", "feeder_field": "FEEDER_ID"},
    "customer":    {"layer": "Customers", "id_field": "CUST_ID", "transformer_key": "DSS_ID", "sensitive_fields": ["NAME", "PHONE", "ADDRESS"]},
    "pole":        {"layer": "Poles", "id_field": "POLE_ID"},
    "feeder_11kv": {"layer": "11kV Feeders", "id_field": "FEEDER_ID"}
  },
  "metric_crs": "EPSG:32631",
  "overload_threshold": 1.0
}
```
First run: if no map exists, the copilot proposes one from layer names/fields and asks the user to confirm in the settings dialog. Never silently guess roles for write/output actions.

### System prompt (stored in `resources/prompts/system.md`, versioned)
Must instruct the model to: act as a GIS assistant inside QGIS; call `inspect_layers` before assuming layer/field names; prefer the schema map; use tools instead of guessing counts; state units and CRS assumptions; explain results briefly with the numbers returned by tools (never invent numbers); say when a request cannot be done with the available tools; ask one clarifying question when a request is ambiguous (e.g. "which feeder?" when none is selected). It must **not** claim an action happened unless a tool result confirms it.

"Along this feeder" handling: if exactly one feeder feature is selected, use it; otherwise ask the user to select or name one.

---

## 8. UX requirements

- Dock panel, dockable left/right, remembers visibility and size.
- Chat view: user bubbles, assistant bubbles (Markdown-lite: bold, lists, code), collapsible **tool-step rows** ("Ran `spatial_select` · 312 selected · 0.8 s") so the user can see what happened.
- Input: multi-line, Enter to send, Shift+Enter newline, **Stop** button while running, **Clear chat** and **New session** actions.
- Status line: provider/model, read-only mode indicator, token/usage hint.
- Errors are human readable ("Layer 'Poles' not found. Available: ...") with a technical detail expander.
- Selection tools show "Undo selection" on the step row.
- Offline/no-key states handled with clear messages, never a traceback.

---

## 9. Coding conventions

- Type hints everywhere in `core/`. Dataclasses for message and result types.
- Small modules, single responsibility; functions under ~40 lines where reasonable.
- Imports: `from qgis.PyQt.QtCore import ...` (never `PyQt5`). `from qgis.core import ...`.
- Logging via `QgsMessageLog.logMessage(msg, "GeoUtility Copilot", level)`; **no `print`**.
- User-visible strings wrapped for translation: `self.tr()` / `QCoreApplication.translate`.
- No global mutable state; plugin state lives on the plugin/controller objects. `unload()` must disconnect every signal, delete the dock, remove actions and cancel running tasks (test reload twice with Plugin Reloader).
- Docstrings: one-line summary + args for public functions. Comments explain **why**, not what.
- Naming: tools `snake_case`; classes `PascalCase`; files `snake_case`.
- Commits: Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`), small and frequent, one logical change each.

---

## 10. Testing requirements

- **Unit tests (no network, no QGIS GUI):** agent loop with `FakeProvider` scripting tool-call sequences; safety policy matrix (every tier × read-only on/off × approve/reject); schema-map parsing; argument validation; provider wire-format translation using recorded JSON fixtures.
- **Tool tests (QGIS headless via `pytest-qgis`):** each tool against tiny synthetic GeoPackage fixtures in `tests/data/` with known answers (e.g. 10 transformers, 3 without customers; poles at known distances from a feeder line in a projected CRS, plus a geographic-CRS variant to prove reprojection).
- **Edge cases that must have tests:** empty layer, layer without CRS, null/invalid geometries, field name case differences, duplicate keys, CRS mismatch between layers, expression syntax error, layer removed mid-conversation, huge feature count (cap respected).
- **Manual smoke checklist** in `BUILD_PLAN.md` per milestone; run it inside real QGIS before declaring a milestone done.
- Never call the live Claude API in CI. A single opt-in integration test may exist, gated by an env var, never run by default.
- Never commit real IBEDC/customer data. Fixtures are synthetic only.

---

## 11. Definition of done (applies to every task)

1. Code follows sections 2, 3 and 9; ruff and black pass.
2. Relevant tests written and passing; no network in tests.
3. Plugin loads, unloads and **reloads twice** in QGIS with no errors in the Log Messages panel.
4. UI never freezes during an LLM call or Processing run.
5. Any new tool has: description for the model, JSON schema, risk tier, `preview()`, validation, tests, and an entry in the audit log.
6. Docs updated (`README.md` for users, this file if architecture or rules changed).
7. You summarise what changed, what you verified, and what you could not verify.

---

## 12. How agents should work in this repo

- **Plan first.** For any task larger than a trivial fix, post a short plan (files to touch, approach, risks) and wait for confirmation before coding.
- **Work milestone by milestone** as defined in `BUILD_PLAN.md`. Do not start the next milestone without being asked. Do not build out-of-scope items (section 1).
- **Smallest working increment.** Get one vertical slice working end to end before broadening.
- **Do not invent QGIS or Anthropic API details from memory.** When unsure about a PyQGIS class, Processing algorithm id/parameters or Anthropic request/response shape, check the official documentation (QGIS PyQGIS API docs, `processing.algorithmHelp()` in the QGIS Python console, Anthropic API docs) and say what you verified. For algorithm parameters, introspect with `QgsApplication.processingRegistry().algorithmById(...)`.
- **Ask when ambiguous** rather than guessing field names, CRS choices or safety behaviour.
- **Never** run destructive commands (`rm -rf`, force pushes, dropping DB objects), change files outside the repo, or touch the user's real QGIS profile data except through the documented dev-link scripts.
- **Never** hard-code secrets, add telemetry, or send data anywhere except the configured LLM endpoint.
- **Report honestly.** If something is untested or you are unsure, say so. Do not claim success without evidence (test output, log lines, a described manual check).
- Keep a running `CHANGELOG.md`; each milestone ends with a tagged commit (`v0.1.0`, `v0.2.0`, `v0.3.0`).

---

## 13. Glossary (domain)

- **DSS**: Distribution Substation (11kV/415V transformer + protection), the typical unit of "transformer" in this domain.
- **11kV feeder**: medium-voltage line supplying DSS transformers.
- **Overloaded transformer**: load exceeds a configurable fraction of rated capacity (default threshold 1.0 × rated kVA, from the schema map).
- **Orphan transformer**: DSS with no connected customers (by key or by spatial proximity).
