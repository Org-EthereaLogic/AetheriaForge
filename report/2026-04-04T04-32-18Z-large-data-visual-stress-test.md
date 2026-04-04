# Large-Data Visual Stress Test Report

| Field | Value |
| --- | --- |
| Date | 2026-04-04T04:32:18Z |
| Scope | End-to-end visual and performance stress test of the Gradio operator dashboard |
| Dataset | 60 synthetic forge contracts, 5,500 synthetic evidence artifacts |
| Data span | 34 days (2026-03-01 through 2026-04-03) |
| Datasets simulated | 15 real-world-inspired datasets (chicago_crimes, nyc_311_requests, etc.) |
| Verdict distribution | PASS: 3,057 / WARN: 1,375 / FAIL: 1,068 |

## Test Environment

- macOS Darwin 25.3.0 (Apple Silicon)
- Python 3.14.3, Gradio (installed via uv)
- Contracts directory: `/tmp/aetheriaforge_stress/contracts` (60 YAML files)
- Evidence directory: `/tmp/aetheriaforge_stress/evidence` (5,500 JSON files)
- All 166 existing tests passing before and after changes

## Tabs Exercised

### 1. Forge Registry

- Auto-loads on startup with 60 contracts
- Table renders all 60 rows with correct dataset names, versions, source/target, engine, and thresholds
- Brand logo, header, and description display correctly
- No visual glitches observed

### 2. Transformation Status

- Queried 5,500 artifacts successfully (truncated to 1,000 rows in table)
- Dataset filter tested with "chicago_crimes" (367 artifacts returned correctly)
- Verdict filter dropdown functional
- Date filter fields present and operational
- Table row data (filename, dataset, verdict circle, coherence, records, timestamp) all correct

### 3. Evidence Explorer

- Loaded a single artifact by filename
- Metadata summary line (Dataset, Verdict, Coherence, Timestamp) renders correctly
- Full JSON payload displayed with syntax highlighting
- Evidence directory syncs from Transformation Status tab

### 4. Analytics

- All four charts rendered with 5,500 artifacts
- Verdict Distribution bar chart: PASS/WARN/FAIL counts match
- Coherence Score Distribution histogram: reasonable distribution shape
- Daily Activity Volume: 34 daily bars
- Coherence Trend: 34-day line chart with expected variance
- Color Theme dropdown available (Brand, Traffic Light, Colorblind Safe, Cyberpunk, Pastel)

## Issues Found and Fixed

### Issue 1: Summary verdict counts from truncated data (HIGH)

**Location:** `app/app.py:82-111` (`_build_summary_line_with_total`)

**Problem:** When 5,500 artifacts were queried but the table was truncated to 1,000
rows, the summary showed `PASS: 544 | WARN: 265 | FAIL: 191` (= 1,000), while
the header claimed "5500 artifacts". The verdict breakdown was misleading because
it only counted the truncated visible rows.

**Fix:** Added `verdict_counts` parameter to `_build_summary_line_with_total`.
Modified `_query_evidence_records` to compute verdict counts from all results
before truncation and pass them through. The summary now correctly shows
`PASS: 3057 | WARN: 1375 | FAIL: 1068` (= 5,500).

**Files changed:** `app/app.py`

### Issue 2: X-axis date labels overlap on charts (MEDIUM)

**Location:** `app/analytics.py:132-142, 166-176`

**Problem:** The Daily Activity Volume and Coherence Trend charts had 34 date
labels on the x-axis, all rendered at the same density. Labels overlapped and
were difficult to read.

**Fix:** Added `tickangle=-45` and `dtick=max(1, len(days) // 15)` to both
chart x-axis configurations. This rotates labels and shows every Nth date
to prevent overlap while preserving readability.

**Files changed:** `app/analytics.py`

### Issue 3: App startup hangs on page load (HIGH)

**Location:** `app/app.py:667-673` (`app.load` callback)

**Problem:** The `app.load` callback used `_load_registry_with_status` which
accepts a `gr.Progress` parameter, but the load callback used `queue=False`.
The `gr.Progress` call blocks when the queue is disabled, causing the page to
hang indefinitely on "Loading..." during startup.

**Fix:** Created a dedicated `_load_registry_on_startup` function without
`gr.Progress` for the `app.load` callback. The progress-enabled version is
still used for the manual "Load Registry" button click (which uses `queue=True`).

**Files changed:** `app/app.py`

### Issue 4: ThreadPoolExecutor unbounded workers (MEDIUM)

**Location:** `src/aetheriaforge/evidence/history.py:84`

**Problem:** `ThreadPoolExecutor()` without `max_workers` would spawn one
thread per file when parsing 5,500 evidence artifacts, creating excessive
thread overhead.

**Fix:** Bounded to `min(8, len(paths))` workers, limiting thread creation
while still parallelizing I/O for large evidence directories.

**Files changed:** `src/aetheriaforge/evidence/history.py`

### Issue 5: Unbounded class-level artifact cache (LOW)

**Location:** `src/aetheriaforge/evidence/history.py:36`

**Problem:** `TransformationHistory._cache` is a class-level dict that grows
without bound. In long-running deployments with many different evidence
directories, this could accumulate stale entries.

**Fix:** Added `_CACHE_MAX_ENTRIES = 8` limit with FIFO eviction when the
cache exceeds the bound.

**Files changed:** `src/aetheriaforge/evidence/history.py`

## Verification

| Check | Result |
| --- | --- |
| `uv run ruff check .` | All checks passed |
| `uv run mypy src/aetheriaforge tests` | Success: no issues found in 39 source files |
| `uv run pytest` | 166 passed in 1.39s |
| Summary verdict counts (API) | 5500 = 3057 + 1375 + 1068 (verified) |
| Summary verdict counts (UI) | Visually confirmed PASS: 3057, WARN: 1375, FAIL: 1068 |
| App startup time | Instant load (no hang) with 60 contracts |
| Analytics chart labels | Rotated -45 degrees, every 2nd date shown, readable |
| Filtered query (chicago_crimes) | 367 artifacts, correct verdict breakdown |
| Evidence Explorer artifact load | Metadata and JSON rendered correctly |

## Files Changed

| File | Changes |
| --- | --- |
| `app/app.py` | Fixed verdict counts from full dataset; fixed app.load hang |
| `app/analytics.py` | Fixed x-axis date label overlap on two charts |
| `src/aetheriaforge/evidence/history.py` | Bounded ThreadPoolExecutor; bounded cache |
