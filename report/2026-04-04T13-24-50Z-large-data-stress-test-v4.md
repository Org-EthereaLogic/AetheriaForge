# Large-Scale Real-World Stress Test v4

| Field | Value |
| --- | --- |
| Date | 2026-04-04T13:24:50Z |
| Author | Claude Opus 4.6 (1M context) |
| Scope | End-to-end stress test with 9 real-world datasets, performance optimization, visual app validation |
| Total records processed | 13,506,403 |
| Total data volume | ~1.17 GB on disk |
| Outcome | All 9 datasets PASS through full pipeline; 3 performance optimizations applied |

## Datasets Used

| Dataset | Source | Rows | Columns | File Size |
| --- | --- | ---: | ---: | --- |
| yellow_taxi_jan | NYC TLC January 2024 (Parquet) | 2,964,624 | 19 | 47.6 MB |
| yellow_taxi_jun | NYC TLC June 2024 (Parquet) | 3,539,193 | 19 | 57.1 MB |
| yellow_taxi_oct | NYC TLC October 2024 (Parquet) | 3,833,771 | 19 | 61.4 MB |
| us_counties_covid | NYT US Counties COVID (CSV) | 2,502,832 | 6 | 99.9 MB |
| earthquakes | USGS Historical Earthquakes (CSV) | 20,000 | 22 | 3.7 MB |
| earthquakes_30day | USGS 30-Day Feed (CSV) | 11,091 | 22 | 2.1 MB |
| air_quality | OpenAQ Air Quality (CSV) | 18,862 | 12 | 2.1 MB |
| epa_aqi_2024 | EPA Daily AQI by County 2024 (CSV) | 329,166 | 10 | 25.4 MB |
| github_events | GitHub Archive Events (JSONL) | 286,864 | 8 | 869.8 MB |

## Pipeline Results

All 9 datasets passed the full forge pipeline (ingest, schema enforcement,
coherence scoring, evidence writing):

| Dataset | Coherence Score | Pipeline Verdict | Time |
| --- | ---: | --- | ---: |
| yellow_taxi_jan | 0.975083 | PASS | 0.562s |
| yellow_taxi_jun | 0.951225 | PASS | 0.632s |
| yellow_taxi_oct | 0.955500 | PASS | 0.691s |
| us_counties_covid | 0.999972 | PASS | 0.057s |
| earthquakes | 0.966680 | PASS | 0.028s |
| earthquakes_30day | 0.818627 | PASS | 0.019s |
| air_quality | 1.000000 | PASS | 0.009s |
| epa_aqi_2024 | 1.000000 | PASS | 0.012s |
| github_events | 0.965138 | PASS | 0.475s |

## Entity Resolution Results

| Test | Primary | Secondary | Resolved | Unresolved | Ambiguous | Time |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| earthquakes x air_quality | 5,000 | 5,000 | 0 | 5,000 | 0 | 0.017s |

Zero matches expected (location formats differ between USGS and OpenAQ).

## Temporal Reconciliation Results

| Test | Input Rows | Reconciled | Conflicts | Time |
| --- | ---: | ---: | ---: | ---: |
| COVID New York | 45,692 | 59 | 0 | 0.007s |
| COVID California | 45,693 | 59 | 0 | 0.007s |
| EPA AQI 2024 | 329,166 | 996 | 0 | 0.151s |

## Performance Optimizations Applied

### 1. Entropy: nested object detection (12.7x speedup)

**File:** `src/aetheriaforge/forge/entropy.py`

**Problem:** `column_entropy()` called `.astype(str)` on all rows of object
columns containing deeply nested dicts/lists (e.g. GitHub event payloads).
The existing sampling fast-path relied on `value_counts()` raising `TypeError`
for unhashable values, but modern pandas can hash dicts, so the fast-path
never triggered.

**Fix:** Added `_has_nested_values()` probe that checks the first 20 values
for `dict`/`list` types. When detected and column size exceeds 10K rows,
deterministic sampling caps string conversion at 10K rows instead of the
full column.

**Impact:** github_events entropy scoring: 5.620s -> 0.444s (12.7x faster).

### 2. Entropy: parallel column scoring (1.2-2.6x speedup)

**File:** `src/aetheriaforge/forge/entropy.py`

**Problem:** `shannon_coherence_score()` computed per-column entropy
sequentially. For wide DataFrames (19+ columns), this left CPU cores idle.

**Fix:** Added `_compute_column_entropies()` that parallelizes across columns
using `ThreadPoolExecutor` when the column count exceeds 4. Also pre-computes
both source and forged entropies separately to maximize parallelism.

**Impact:** yellow_taxi (19 cols): 0.673s -> 0.555s; us_counties (6 cols):
0.138s -> 0.054s.

### 3. Ingest: chunked JSONL reading (2.1x memory reduction)

**File:** `src/aetheriaforge/ingest/reader.py`

**Problem:** `pd.read_json(lines=True)` loaded entire file into memory,
causing 15.9 GB peak RSS for an 870 MB JSONL file (18x amplification from
nested JSON structures).

**Fix:** For JSONL files > 100 MB, the reader now uses `chunksize=50_000`
to read incrementally and concatenates chunks. This reduces peak memory by
allowing pandas to GC intermediate parse buffers between chunks.

**Impact:** github_events ingest memory: 15,970 MB -> 7,530 MB (2.1x
reduction).

### 4. Schema enforcer: lazy copy (memory reduction)

**File:** `src/aetheriaforge/schema/enforcer.py`

**Problem:** `enforce()` unconditionally called `df.copy()` at the start,
doubling memory even when no type coercions were needed (common case for
schema-conformant data).

**Fix:** Deferred the copy until the first column actually requires coercion.
When all columns already match their spec dtypes, no copy is made.

**Impact:** Eliminates unnecessary DataFrame duplication for the common
no-coercion path across all 9 datasets.

## Evidence System

- 22 evidence artifacts written across all pipeline stages
- Evidence list, query, and summary operations all < 10ms
- Thread-pooled artifact parsing with directory-signature caching confirmed working

## Visual App Validation

All 4 Gradio dashboard tabs verified with Kapture browser automation:

1. **Forge Registry** -- 9 contracts loaded, table renders correctly
2. **Transformation Status** -- 22 artifacts displayed with correct verdict
   badges, coherence scores, record counts, mode indicators, and summary line
3. **Evidence Explorer** -- Full JSON artifact detail loads correctly with
   metadata summary
4. **Analytics** -- All 4 Plotly charts render: verdict distribution, coherence
   histogram, daily volume, coherence trend

## Regression Check

- 227 tests pass (0 failures, 0 errors)
- Lint: all checks passed
- Type check: no issues found
- No placeholder markers detected

## Residual Notes

- github_events JSONL ingestion still uses 7.5 GB for 870 MB of deeply nested
  JSON. This is a pandas limitation with nested structures. Further reduction
  would require dropping nested columns before ingest or using a streaming
  JSON parser (ijson/orjson).
- Entity resolution between earthquakes and air quality produces 0 matches
  (expected -- location formats are incompatible between USGS and OpenAQ).
  A fuzzy matching strategy would be needed for cross-source geographic
  resolution.
