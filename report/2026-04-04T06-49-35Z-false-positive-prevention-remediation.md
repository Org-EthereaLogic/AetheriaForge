# False-Positive Prevention Remediation

**Date:** 2026-04-04T06:49:35Z
**Trigger:** DriftSentinel post-mortem revealed that published enterprise tools
were producing misleading PASS/FAIL verdicts from demo/synthetic data while
appearing to process real user data. AetheriaForge was audited for the same
class of issue.

## Audit Findings

### Root Cause (DriftSentinel)

DriftSentinel's `run_dataset_pipeline()` registered real dataset identities but
executed demo helpers under the hood. Evidence artifacts were tagged with real
dataset names while containing verdicts derived from synthetic data. The
published app displayed these as authoritative production results.

### AetheriaForge Risk Profile

AetheriaForge had the same structural risk through a different mechanism:

1. **No provenance in evidence artifacts.** `PipelineResult.as_dict()` never
   wrote `source_location`, `target_location`, `contract_version`, or
   `execution_mode`. Demo and real evidence were byte-identical.

2. **Notebook 02 wrote real evidence from synthetic data unconditionally.**
   Five hardcoded rows produced a PASS artifact in the same directory the app
   reads from.

3. **Bundle job invoked the demo notebook.** `catalog`/`schema` params were
   passed but never used in the notebook's data loading logic.

4. **Default paths formed a closed loop.** `/tmp/aetheriaforge_evidence` was
   the default in the notebook, `app.yaml`, and `aetheriaforge_app.yml`.
   Zero-config deployment displayed demo verdicts as production.

5. **App had zero provenance awareness.** Dashboard displayed all artifacts
   identically regardless of origin.

6. **Tests never verified evidence content.** Only checked file existence,
   never JSON fields.

### Key Difference from DriftSentinel

The AetheriaForge library itself (`src/aetheriaforge/`) had NO demo mode, NO
synthetic data, NO fallback paths. The forge engine is a pure compute layer
that scores whatever DataFrames it receives. The contamination risk was
entirely in the notebook surface, the bundle job wiring, and the absence of
provenance in the artifact schema.

## Remediation Actions

### 1. Provenance Tracking in Evidence Artifacts

**File:** `src/aetheriaforge/orchestration/pipeline.py`

Added four provenance fields to `PipelineResult`:
- `execution_mode` (default: `"unverified"`) — distinguishes `demo`,
  `notebook`, `contract_backed`, and `unverified` runs
- `source_location` — `catalog.schema.table` from the contract
- `target_location` — `catalog.schema.table` from the contract
- `contract_version` — dataset version from the contract

All four fields are serialized into `as_dict()` and therefore written to every
evidence artifact. An `EXECUTION_MODES` frozen set enforces valid values, and
`ForgePipeline.run()` raises `ValueError` on invalid modes.

### 2. Runner Provenance Threading

**File:** `src/aetheriaforge/orchestration/runner.py`

Added `execution_mode` field to `DatasetInput` (default: `"unverified"`).
`ForgeRunner.run_one()` threads this through to `ForgePipeline.run()`.

### 3. Notebook Demo Guard

**File:** `notebooks/02_run_forge_pipeline.py`

The notebook now branches on `catalog`:
- When `catalog` is set: reads real data from Unity Catalog via
  `spark.table()` and sets `execution_mode = "contract_backed"`.
- When `catalog` is blank: uses synthetic data with a prominent WARNING banner
  and sets `execution_mode = "demo"`.

Evidence artifacts from demo runs are now permanently tagged `"demo"` and
visually distinguished in the dashboard.

### 4. Bundle Job Parameters

**File:** `resources/forge_job.yml` and `databricks.yml`

The bundle job now passes `contract_path` and `evidence_dir` to the notebook.
Corresponding variables were added to `databricks.yml` with safe defaults.

### 5. Dashboard Provenance Display

**File:** `app/app.py`

- Transformation Status table now includes a **Mode** column with visual
  indicators: `contract_backed`, `demo`, `notebook`, `unverified`.
- Evidence Explorer metadata now shows **Mode**, **Source**, and **Contract**
  version alongside existing verdict and coherence display.

### 6. Test Coverage

Added 13 new tests across 4 test files:

| Test File | New Tests | What They Verify |
|-----------|-----------|------------------|
| `test_orchestration.py` | 7 | execution_mode threading, validation, provenance in result and artifact JSON |
| `test_runner.py` | 3 | execution_mode threading, default mode, batch evidence provenance |
| `test_app.py` | 2 | mode column display, contract_backed mode display |
| `test_governance_guards.py` | 1 | bundle variables include contract_path and evidence_dir |

Existing tests updated:
- `test_pipeline_result_as_dict` now asserts provenance fields
- `test_forge_writes_evidence` now verifies artifact JSON content
- `test_valid_file` (meta) now verifies provenance in metadata display
- Evidence fixtures updated to include provenance fields

## Verification

```
uv run ruff check .           PASS
uv run mypy src/aetheriaforge tests  PASS (39 source files)
uv run pytest -q              PASS (179 tests)
```

## Files Changed

| File | Change |
|------|--------|
| `src/aetheriaforge/orchestration/pipeline.py` | Added provenance fields, execution_mode validation |
| `src/aetheriaforge/orchestration/runner.py` | Added execution_mode to DatasetInput |
| `src/aetheriaforge/orchestration/__init__.py` | Exported EXECUTION_MODES |
| `app/app.py` | Added Mode column, provenance in metadata display |
| `notebooks/02_run_forge_pipeline.py` | Demo/contract-backed branching, execution_mode tagging |
| `resources/forge_job.yml` | Added contract_path and evidence_dir parameters |
| `databricks.yml` | Added contract_path and evidence_dir variables |
| `tests/test_orchestration.py` | 7 new provenance tests |
| `tests/test_runner.py` | 3 new provenance tests |
| `tests/test_app.py` | Updated fixtures, 2 new mode display tests |
| `tests/test_forge_engine.py` | Evidence content verification |
| `tests/test_governance_guards.py` | 1 new bundle variable test |

## Impact on Existing Evidence

Any evidence artifacts generated before this remediation do NOT contain
`execution_mode`, `source_location`, `target_location`, or `contract_version`.
The dashboard handles these gracefully:
- Missing `execution_mode` defaults to `"unverified"` display
- Missing provenance fields are omitted from metadata

Pre-remediation artifacts should be treated as unverified. They are not
automatically invalid, but they cannot prove what data source was used.

## Contrast with DriftSentinel

| Aspect | DriftSentinel | AetheriaForge |
|--------|---------------|---------------|
| Demo code in library | Yes (`run_intake_demo()`, `run_drift_demo()`) | No |
| Fallback paths | Yes (silent demo fallback) | No |
| Provenance in artifacts | Missing (pre-fix) | Missing (pre-fix), now added |
| Notebook risk | Demo notebook as default job | Same, now guarded |
| Fix scope | Runtime rewrite + contract loader | Provenance schema + notebook guard |
