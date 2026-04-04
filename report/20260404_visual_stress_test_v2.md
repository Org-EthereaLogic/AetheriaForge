# Visual Stress Test v2 — 2026-04-04

## Scope

- Surface: local Gradio app at `http://127.0.0.1:7860`
- Contracts directory: `/tmp/aetheriaforge_contracts` (10 contracts)
- Evidence directory: `/tmp/aetheriaforge_evidence` (5049 artifacts)
- Browser automation: Chrome via Claude-in-Chrome MCP
- Viewport: ~1176x1022 (desktop)

## Pre-Test Baseline

| Check | Result |
| --- | --- |
| `uv sync --all-groups` | 84 packages audited |
| Placeholder scan | Clean |
| `uv run ruff check .` | All checks passed |
| `uv run pytest` | 162 passed in 1.40s |

## Tab-by-Tab Walkthrough

### Tab 1: Forge Registry

- Auto-loads 10 contracts on page load
- Status line shows "10 contracts registered"
- **Issue found**: "Silver Threshold" column header and values truncated/clipped on right edge due to long `catalog.schema.table` paths in Source/Target columns consuming all horizontal space

### Tab 2: Transformation Status

- Empty state shows proper prompt text
- Query button loads 5049 artifacts instantly (<1s)
- Summary line correctly shows verdict breakdown: PASS: 1287, WARN: 2497, FAIL: 1265
- Filters accordion opens/closes properly
- Verdict dropdown (PASS/WARN/FAIL) works — filtering to FAIL showed 1265 artifacts, all FAIL
- Date range filters are accessible

### Tab 3: Evidence Explorer

- Row-click navigation from Transformation Status works correctly
  - Auto-switches to Evidence Explorer tab
  - Populates filename, loads JSON artifact, shows metadata summary
- Metadata summary line renders dataset, verdict (with colored circle), coherence score, timestamp
- JSON payload renders with syntax highlighting in code viewer

### Tab 4: Analytics

- **Issue found**: Bottom two charts (Daily Activity Volume, Coherence Trend) cut off — x-axis labels and lower portions not visible; page could not scroll to reveal them
- Color theme switcher works correctly across all 5 themes: Brand, Traffic Light, Colorblind Safe, Cyberpunk, Pastel
- All 4 charts render correctly with data: Verdict Distribution, Coherence Score Distribution, Daily Activity Volume, Coherence Trend

### Console

- No JavaScript errors or warnings on page load or interaction

## Issues Found and Resolved

### Issue 1: Registry table last column truncated

- **Severity**: Medium
- **Symptom**: "Silver Threshold" column header shows "Sil..." and values are clipped at right edge
- **Root cause**: Source/Target columns display full `catalog.schema.table` paths (e.g., `bronze_catalog.raw.payment_transactions_raw`), consuming all available horizontal space and pushing the last column off-screen. Gradio's internal `.disable_click` button wrapper and `.table-container` both use `overflow: hidden`, preventing horizontal scroll.
- **Fix applied** (3 changes in `app/app.py`):
  1. Renamed header from "Silver Threshold" to "Silver Min" (shorter)
  2. Shortened Source/Target display to `schema.table` format (dropped redundant catalog prefix)
  3. Added CSS overrides for `.table-container` (`overflow-x: auto`) and `.disable_click` (`overflow: visible`) as a safety net for wide tables
  4. Added `column_widths` and `wrap=True` for proportional column sizing

### Issue 2: Analytics bottom charts cut off

- **Severity**: High
- **Symptom**: Daily Activity Volume and Coherence Trend charts have x-axis labels, date ticks, and lower y-axis clipped. Page cannot scroll further to reveal them.
- **Root cause**: Plotly figures in `_LAYOUT_DEFAULTS` had no explicit `height`, so Gradio used its default plot height. Four charts in a 2x2 grid exceeded the viewport height.
- **Fix applied** (`app/analytics.py`):
  - Added `"height": 320` to `_LAYOUT_DEFAULTS` so all four charts fit within a single viewport without scrolling.

## Code Changes

| File | Change |
| --- | --- |
| `app/app.py:121-122` | Source/Target display shortened to `schema.table` |
| `app/app.py:298-308` | CSS overrides for table container horizontal scroll |
| `app/app.py:370` | Header renamed "Silver Threshold" to "Silver Min" |
| `app/app.py:372-373` | Added `column_widths` and `wrap=True` |
| `app/analytics.py:44` | Added `height: 320` to Plotly layout defaults |

## Post-Fix Verification

| Check | Result |
| --- | --- |
| `uv run ruff check .` | All checks passed |
| `uv run pytest` | 162 passed in 1.45s |
| Registry table | All 6 columns fully visible without horizontal scroll |
| Analytics charts | All 4 charts fully visible within viewport with axis labels |
| Other tabs | No regressions observed |

## Interpretation

- The two issues were purely visual/layout — no data correctness or performance problems found.
- The 5049-artifact dataset loaded instantly across all views, confirming the `queue=False` optimization from the previous stress test session holds.
- The theme switcher, filters, cross-tab navigation, and JSON viewer all function correctly.
- No console errors observed during the full walkthrough.
