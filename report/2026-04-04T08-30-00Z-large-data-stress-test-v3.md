# Large-Scale Real-World Stress Test Report

| Field | Value |
| --- | --- |
| Date | 2026-04-04 |
| Author | Claude Opus 4.6 (1M context) |
| Scope | End-to-end stress test with 5 real-world datasets across 7 pipeline phases |
| Outcome | All phases pass. Three performance fixes applied. Databricks App deployed. |

## Datasets

| Dataset | Source | Format | Size | Rows | Columns |
| --- | --- | --- | --- | --- | --- |
| NYC Yellow Taxi Jan 2024 | TLC | Parquet | 48 MB | 2,964,624 | 19 |
| NYT COVID US Counties | NYT | CSV | 100 MB | 2,502,832 | 6 |
| USGS Earthquakes 2020-2025 | USGS | CSV | 3.7 MB | 20,000 | 22 |
| NYC Air Quality | NYC Open Data | CSV | 2.1 MB | 18,862 | 12 |
| GitHub Archive Events | GH Archive | JSONL | 870 MB | 286,864 | 8 |

Total: **8,793,182 records** across 5 datasets, 1.02 GB on disk.

## Performance Results (Post-Optimization)

### Phase 1: File Ingestion

| Dataset | Time | Notes |
| --- | --- | --- |
| yellow_taxi (Parquet) | 0.10s | Parquet reader excellent |
| us_counties_covid (CSV) | 0.69s | 100 MB CSV |
| earthquakes (CSV) | 0.04s | Small CSV |
| air_quality (CSV) | 0.01s | Small CSV |
| github_events (JSONL) | 5.20s | 870 MB JSONL with nested objects |

### Phase 2: Shannon Entropy Scoring

| Dataset | Time | Score | Forged Rows |
| --- | --- | --- | --- |
| yellow_taxi | 0.75s | 0.975083 | 2,824,462 |
| us_counties_covid | 0.15s | 0.999972 | 2,500,204 |
| earthquakes | 0.03s | 0.966680 | 15,735 |
| air_quality | 0.01s | 1.000000 | 18,862 |
| github_events | 6.06s | 0.922886 | 63,362 |

### Phase 3: Full Forge Pipeline

| Dataset | Time | Verdict | Coherence |
| --- | --- | --- | --- |
| yellow_taxi | 0.77s | PASS | 0.975083 |
| us_counties_covid | 0.15s | PASS | 0.999972 |
| earthquakes | 0.03s | PASS | 0.966680 |
| air_quality | 0.01s | PASS | 1.000000 |
| github_events | 5.97s | PASS | 0.922886 |

### Phase 4: Entity Resolution

| Test | Time | Result |
| --- | --- | --- |
| earthquakes x air_quality (10K rows) | 0.08s | 0 resolved, 5000 unresolved |

### Phase 5: Temporal Reconciliation

| Test | Time | Result |
| --- | --- | --- |
| COVID New York (45,692 rows) | 0.02s | 59 reconciled, 0 conflicts |

### Phase 6: Evidence System

12 evidence artifacts written and queried successfully in <10ms.

## Issues Found and Resolved

### Issue 1: Entropy Scoring Hangs on Object Columns (Critical)

**Symptom:** `shannon_coherence_score` hung indefinitely on the GitHub events
dataset (286K rows with nested dict/list columns from JSON).

**Root cause:** `value_counts(dropna=False)` on columns with unhashable Python
objects (nested dicts/lists) causes catastrophic hashing overhead. The initial
`astype(str)` fix resolved the hang but was still slow (56s with tracemalloc,
6s without).

**Fix applied:** Added deterministic sampling for large object columns
(>50K rows) that contain unhashable types. Samples 50K evenly-spaced rows
and converts to string for counting. Result is within ~1% accuracy of full
computation.

**File:** `src/aetheriaforge/forge/entropy.py`

**Before:** Hung indefinitely on nested object columns.
**After:** 6.06s for 286K rows with 4 nested object columns.

### Issue 2: Entity Resolver O(n^2) Row-by-Row Iteration (Major)

**Symptom:** `EntityResolver._resolve_exact` iterated per-row in Python with
per-row mask operations on the full merged DataFrame.

**Root cause:** The original implementation used a Python for-loop over every
primary row, building a boolean mask for each row and filtering the merged
DataFrame. This is O(n * m) where n is primary rows and m is merged rows.

**Fix applied:** Replaced with vectorized pandas merge + groupby operations.
Match counts computed via groupby on the merged DataFrame. Resolved/unresolved
rows selected via boolean indexing. Match decisions sampled (max 1000) to
avoid memory explosion on large datasets.

**File:** `src/aetheriaforge/resolution/resolver.py`

**Before:** O(n^2) with Python iteration.
**After:** O(n log n) vectorized. 10K rows resolve in 0.08s.

### Issue 3: Temporal Reconciler Row-by-Row Group Iteration (Major)

**Symptom:** `TemporalReconciler._reconcile_latest_wins` iterated over every
group in Python, building row dicts one at a time.

**Fix applied:** Replaced with vectorized `sort_values` + `groupby.first()`
for the main reconciliation. Conflict detection via `transform("max")` and
group counting instead of per-group Python inspection.

**File:** `src/aetheriaforge/temporal/reconciler.py`

**Before:** Per-group Python iteration with list append.
**After:** Vectorized. 45K rows reconcile in 0.02s.

### Issue 4: tracemalloc 9x Overhead (Diagnostic Finding)

**Symptom:** GitHub events entropy scoring took 56s with tracemalloc enabled
vs 6s without — a 9.2x overhead.

**Root cause:** tracemalloc tracks every allocation. The entropy scoring
creates millions of temporary string objects during `astype(str)`, and
tracking each allocation dominates execution time.

**Fix applied:** Replaced tracemalloc in the stress test with process RSS
delta measurement via `resource.getrusage`. Coarser but zero-overhead.

**File:** `scripts/run_large_scale_stress_test.py`

### Issue 5: App Evidence Display for Non-Pipeline Artifacts (UX)

**Symptom:** Ingest, resolution, and temporal evidence artifacts displayed as
blank rows in the Transformation Status tab (no dataset name, no verdict,
no record counts, no timestamps).

**Fix applied:** Added event-type detection with badge rendering for
non-pipeline artifact types. Derives dataset names from file paths for
ingest results. Shows record counts, resolution outcomes, and temporal
reconciliation stats.

**File:** `app/app.py`, `app/analytics.py`

### Issue 6: Databricks App Deployment Failure (Deployment)

**Symptom:** `gradio: executable file not found in $PATH` when deploying
the Databricks App.

**Root cause:** The `requirements.txt` was only in `app/` but the bundle
`source_code_path` resolves to the repo root. Databricks Apps looks for
`requirements.txt` at the source root.

**Fix applied:** Added `requirements.txt` at the repo root with the
aetheriaforge package (`.`) plus `gradio` and `plotly` dependencies. Also
fixed `app/app.yaml` command path from `app.py` to `app/app.py` to match
the bundle root context.

**Files:** `requirements.txt` (new), `app/app.yaml`, `app/requirements.txt`

## Databricks Deployment Validation

| Check | Result |
| --- | --- |
| `databricks bundle validate` | OK |
| `databricks bundle deploy --target dev` | OK |
| Notebooks deployed (4) | OK |
| App deployed and running | OK |
| App URL accessible (OAuth-protected) | OK |

App URL: `https://aetheriaforge-7474657966305346.aws.databricksapps.com`

## Quality Gates

| Gate | Result |
| --- | --- |
| `uv run ruff check .` | All checks passed |
| `uv run mypy src/aetheriaforge` | 29 files, 0 issues |
| `uv run pytest` | 223 passed in 1.75s |

## Files Changed

| File | Change |
| --- | --- |
| `src/aetheriaforge/forge/entropy.py` | Object column handling + large dataset sampling |
| `src/aetheriaforge/resolution/resolver.py` | Vectorized exact-match resolution |
| `src/aetheriaforge/temporal/reconciler.py` | Vectorized latest_wins reconciliation |
| `app/app.py` | Multi-type evidence display |
| `app/analytics.py` | Timestamp extraction for all artifact types |
| `app/app.yaml` | Fixed command path |
| `app/requirements.txt` | Changed `-e ..` to `.` |
| `requirements.txt` | New: root-level deps for Databricks App |
| `scripts/run_large_scale_stress_test.py` | Comprehensive 7-phase stress test |
