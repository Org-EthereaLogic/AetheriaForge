# AF-IP-005: Phase 5 — Databricks App (Operator Dashboard)

| Field | Value |
| --- | --- |
| Document ID | AF-IP-005 |
| Version | 1.1 |
| Status | Draft |
| Author | Anthony Johnson |
| Date | 2026-04-04 |
| Parent | AF-IP-001 Phase 5 |

## Objective

Build a read-only Gradio operator dashboard that surfaces forge registry,
transformation status, evidence artifacts, and analytics charts. Operators
onboard and review forge outcomes without editing notebooks.

## Scope

- `app/app.py` — main Gradio Blocks application with four tabs
- `app/analytics.py` — Plotly chart builders for the Analytics tab
- `app/app.yaml` — Databricks App runtime configuration
- `app/requirements.txt` — app-specific Python dependencies
- `app/__init__.py` — package marker
- `tests/test_app.py` — unit tests for app helper functions
- `app/README.md` — updated with real contents

## Tab Layout

### Tab 1: Forge Registry

Browse all datasets registered via `DatasetRegistry`. Each row shows dataset
name, version, source location, target location, coherence engine, and
threshold configuration.

**Data source:** `DatasetRegistry.from_directory(contracts_dir)`

**Controls:**
- Contracts directory path text input (default from `CONTRACTS_DIR` env var)
- Load Registry button

**Display:**
- Status line (count of registered datasets or empty-state guidance)
- Table: Dataset Name, Version, Source (schema.table), Target
  (schema.table), Engine, Silver Min

### Tab 2: Transformation Status

Filter and inspect recent forge pipeline evidence. Each row is one pipeline
run artifact from the evidence directory.

**Data source:** `TransformationHistory(evidence_dir)`

**Controls:**
- Evidence directory path text input (default from `EVIDENCE_DIR` env var)
- Query button
- Filters accordion: Dataset Name, Verdict (dropdown: PASS/WARN/FAIL/all),
  Date From, Date To

**Display:**
- Summary line (artifact count with verdict breakdown)
- Table: File, Dataset, Verdict (with colored circles), Coherence Score,
  Records In/Out, Timestamp

### Tab 3: Evidence Explorer

Inspect the full JSON payload of a single evidence artifact. Enter a filename
from the Transformation Status table or click a row to auto-navigate.

**Data source:** Direct JSON file read from evidence directory

**Controls:**
- Evidence directory path text input (synced from Tab 2)
- Artifact filename text input
- Load Artifact button

**Display:**
- Metadata summary line (dataset, verdict, coherence score, timestamp)
- Full JSON code block

### Tab 4: Analytics

Visual breakdown of transformation evidence. Charts powered by Plotly.

**Data source:** `TransformationHistory(evidence_dir).list_all()`

**Controls:**
- Evidence directory path text input
- Color Theme dropdown (Brand, Traffic Light, Colorblind Safe, Cyberpunk,
  Pastel)
- Refresh button

**Charts:**
- Verdict Distribution (bar chart: PASS/WARN/FAIL counts)
- Coherence Score Distribution (bar chart: score histogram buckets)
- Daily Activity Volume (bar chart: artifacts per day)
- Coherence Trend (line chart: average coherence score per day)

## Architecture Decisions

1. **Read-only invariant.** The app never writes evidence, modifies the
   registry, or executes forge pipelines. It is a pure viewer.

2. **Import guard for gradio.** The app uses a `try/except ImportError` guard
   so test imports work without gradio installed in the test environment.

3. **DriftSentinel pattern alignment.** Follow the sibling dashboard structure:
   branded theme, 4 tabs, CSS for empty states, logo support, module-level
   `app`/`demo` variables for Databricks runtime.

4. **Analytics as separate module.** Chart-building logic lives in
   `app/analytics.py` to keep the main app file focused on layout.

5. **Environment-driven paths.** Evidence dir and contracts dir are read from
   environment variables with sensible defaults, matching the bundle resource
   config in `resources/aetheriaforge_app.yml`.

## File Dependencies

| New File | Depends On |
| --- | --- |
| `app/app.py` | `aetheriaforge.config.registry`, `aetheriaforge.config.contract`, `aetheriaforge.evidence.history`, `app/analytics.py` |
| `app/analytics.py` | `plotly` |
| `tests/test_app.py` | `app/app.py` helpers, `aetheriaforge.config.contract`, `aetheriaforge.evidence.writer` |

## Acceptance Criteria

1. `app/app.py` constructs a Gradio Blocks app with four tabs matching the
   layout above.
2. Forge Registry tab loads contracts from a directory and displays them in a
   table.
3. Transformation Status tab queries evidence with optional filters and shows
   verdict-colored rows.
4. Evidence Explorer tab loads and displays full JSON for a selected artifact.
5. Analytics tab renders four Plotly charts from evidence data.
6. Clicking a row in Transformation Status auto-navigates to Evidence Explorer
   with the artifact loaded.
7. The app runs locally via `gradio app/app.py`.
8. The app deploys via the existing bundle resource and deploy script.
9. All helper functions have unit tests in `tests/test_app.py`.
10. `make lint`, `make test` pass with zero failures.

## Test Strategy

Unit tests cover the pure-function helpers (registry table building, evidence
querying, artifact loading, analytics data building) without requiring a
running Gradio server. Tests use `tmp_path` fixtures to create temporary
evidence and contract files.

## Exit Criteria

- All acceptance criteria verified
- `make lint` and `make test` pass
- No placeholder markers in new files
- `app/` directory contains all files listed in Scope
