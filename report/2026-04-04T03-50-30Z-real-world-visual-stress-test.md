# Real-World Visual and Stress Test — 2026-04-04

## Scope

- Surface: local Gradio app at `http://127.0.0.1:7860`
- Contracts directory: `output/real-data-stress/20260404T033925Z/contracts`
- Evidence directory: `output/real-data-stress/20260404T033925Z/evidence`
- Fixture manifest: `output/real-data-stress/20260404T033925Z/manifest.json`
- Browser automation: Playwright CLI wrapper

## Real Dataset Inputs

The stress corpus was generated from official public datasets, streamed from
their source portals and replayed through the local forge pipeline.

1. Chicago Crimes 2001 to Present
   - Catalog: `https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-Present/ijzp-q8t2`
   - Download: `https://data.cityofchicago.org/api/views/ijzp-q8t2/rows.csv?accessType=DOWNLOAD`
2. NYC 311 Service Requests from 2020 to Present
   - Catalog: `https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9`
   - Download: `https://data.cityofnewyork.us/api/views/erm2-nwe9/rows.csv?accessType=DOWNLOAD`
3. NYC Motor Vehicle Collisions - Crashes
   - Catalog: `https://data.cityofnewyork.us/Public-Safety/Motor-Vehicle-Collisions-Crashes/h9gi-nx95`
   - Download: `https://data.cityofnewyork.us/api/views/h9gi-nx95/rows.csv?accessType=DOWNLOAD`

## Fixture Generation Facts

- `scripts/generate_real_world_stress_fixtures.py` created the corpus.
- Total artifacts: `1008`
- Datasets: `3`
- Rows processed per dataset: `56,000`
- Artifact mix per dataset: `112 PASS`, `112 WARN`, `112 FAIL`
- Detailed runs with resolution + temporal stages per dataset: `14`
- Generation runtime: `69.916s`
- Evidence volume on disk: `7.3M`

## Issues Found

### 1. Date filters failed on normal evidence timestamps

- Severity: High
- Symptom:
  - Entering `YYYY-MM-DD` values in the Status tab caused the query to fail.
  - The UI showed `Evidence query failed. Check the directory path.`
  - The table surfaced `(error: can't compare offset-naive and offset-aware datetimes)`.
- Root cause:
  - `app/app.py` parsed date-only filters into naive datetimes, then
    `TransformationHistory.query()` compared them against timezone-aware
    `run_at` values.
- Fix:
  - Added UTC-aware filter parsing for both date-only and datetime inputs.
  - Made `date_to` inclusive through end-of-day semantics.
- Evidence:
  - Before: `output/playwright/20260404-status-date-filter-error-before.png`
  - After: `output/playwright/20260404-status-date-filter-fixed.png`

### 2. Status summary counted the truncation sentinel as a real artifact

- Severity: Medium
- Symptom:
  - The Status tab showed `1001 artifacts | ... | other: 1` even though the
    actual result count was `1008`.
- Root cause:
  - `_build_summary_line()` counted the synthetic truncation marker row
    appended by the UI formatter.
- Fix:
  - Added total-aware summary generation and excluded truncation rows from
    verdict breakdowns.
- Evidence:
  - Before: browser snapshot from the baseline run showed
    `1001 artifacts | ... | other: 1`
  - After: `output/playwright/20260404-status-summary-fixed.png`

### 3. Single-day analytics rendered awkward datetime tick labels

- Severity: Medium
- Symptom:
  - With all artifacts on a single day, the Daily Activity Volume chart showed
    fractional time ticks around midnight instead of a stable date label.
- Root cause:
  - Plotly interpreted the single-day `YYYY-MM-DD` strings as a continuous
    datetime axis.
- Fix:
  - Forced category axes for the daily volume and coherence trend charts.
- Evidence:
  - Before: `output/playwright/20260404-analytics-refresh-before.png`
  - After: `output/playwright/20260404-analytics-fixed.png`

## Performance Notes

- No blocking UI slowness was observed on the 1008-artifact real-data corpus.
- There was still avoidable re-parsing of the same evidence directory across
  Status and Analytics flows.
- Added a directory-signature cache in `TransformationHistory`.

Measured helper timings on the same evidence corpus:

- Before cache:
  - `query_evidence(...)` first call: `0.071s`
  - `build_analytics_data(...)` first call: `0.050s`
- After cache:
  - `query_evidence(...)` second call: `0.0085s`
  - `build_analytics_data(...)` second call: `0.005s`

## Files Changed

- `scripts/generate_real_world_stress_fixtures.py`
- `app/app.py`
- `app/analytics.py`
- `src/aetheriaforge/evidence/history.py`
- `tests/test_app.py`
- `tests/test_history.py`
- governance wording updates to make the required stub-marker scan meaningful:
  - `.claude/commands/*.md`
  - `.claude/agents/*.md`
  - `specs/AF-TP-001_Test_Plan.md`
  - `specs/AF-IP-005_Phase5_Databricks_App.md`
  - `specs/AF-WBS-001_Project_Plan_WBS.md`

## Verification

- Stub-marker scan:
  - `PATTERN='TO''DO|FIX''ME|TB''D|PLACE''HOLDER'; rg -n "$PATTERN" specs .claude CLAUDE.md docs`
  - Result: clean (`rg` exit code `1`, no matches)
- `uv run ruff check .`
  - Result: passed
- `uv run mypy src/aetheriaforge tests`
  - Result: passed
- `uv run pytest`
  - Result: `166 passed`
- `make bundle-catalog-check CATALOG=adb_dev PROFILE=e62-trial`
  - Result: passed
- `make bundle-validate CATALOG=adb_dev PROFILE=e62-trial`
  - Result: passed
- Browser console:
  - `output/playwright/20260404-console-after.txt`
  - Result: `0` errors, `0` warnings

## Residual Notes

- The Playwright MCP browser tool was unusable in this environment because it
  attempted to create `/.playwright-mcp`. Browser validation was completed via
  the repo Playwright CLI wrapper instead.
- No internet best-practice search was required during remediation because the
  failures were deterministic and directly traceable in local code.
