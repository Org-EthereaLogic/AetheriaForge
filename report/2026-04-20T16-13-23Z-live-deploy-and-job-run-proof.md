# Live Deploy + Job Run Proof — 2026-04-20T16:13:23Z

Append-only evidence artifact that closes the residual risk flagged in the
previous `/sync` record (`report/2026-04-20T15-40-51Z-notion-sync-record.md`):
the live `make bundle-validate` run proves auth, bundle resolution, and
workspace validation only; it does not prove a fresh deploy or a job run in
this session. This record proves both against the known-good dev workspace.

## Scope

- Workspace: `e62-trial` profile → `dbc-9cfc36a7-5883.cloud.databricks.com`
- Unity Catalog catalog: `adb_dev` (owner: anthony.johnsonii@etherealogic.ai,
  metastore `1028ccdc-a4f5-4a1f-9421-198861b234dd`)
- Bundle target: `dev`
- Repo HEAD at start: `e913939` (Notion sync record commit)
- Repo HEAD at end: `5b3a9f4` (notebook source-precedence fix; see below)

## Live Deploy — `databricks bundle deploy` (`repo-verified`)

```
databricks bundle deploy -p e62-trial --target dev \
    --var="catalog=adb_dev" \
    --var="schema=default" \
    --var="runtime_volume=aetheriaforge_runtime"
```

**Outcome:**

- `Uploading bundle files to /Workspace/Users/anthony.johnsonii@etherealogic.ai/.bundle/aetheriaforge/dev/files...`
  → **success** (workspace artifacts refreshed, including the patched
  `notebooks/02_run_forge_pipeline.py`).
- `Deploying resources... Updating deployment state...` → **partial**.
  Terraform apply reported:
  ```
  Error: cannot create volume: Volume 'adb_dev.default.aetheriaforge_runtime'
    already exists
  ```
  The volume pre-exists outside the bundle's Terraform state from a prior
  bootstrap run (`created_at: 1775306465958`, `owner:
  anthony.johnsonii@etherealogic.ai`, `volume_id:
  a89b8a34-6574-46c3-af61-63f29885ae72`). Destroying and recreating it would
  delete the 4 pre-existing and 2 newly-written evidence JSON files in it, so
  the orphan state is left in place and flagged as a separate residual ops
  item (see below). Despite the terraform partial failure, the bundle's
  **workspace file push completes unconditionally before resource apply**,
  so the patched notebook is live in the workspace and is the version executed
  by the subsequent job run (confirmed by the job's `execution_mode:
  contract_backed` output). The managed `forge_job` resource remained reachable
  at `https://dbc-9cfc36a7-5883.cloud.databricks.com/jobs/650093448938396`.
- Full console logs persisted at `/tmp/aetheriaforge-live-proof/bundle-deploy.log`
  and `/tmp/aetheriaforge-live-proof/bundle-deploy-2.log` on the runner.

## Live Job Run — `databricks bundle run forge_job` (`repo-verified`)

Two runs were executed. The first failed on a notebook bug, which was fixed
in-repo at commit `5b3a9f4`; the second succeeded.

### Run 1 (pre-fix, FAILED) — `857684359543440`

```
databricks bundle run forge_job -p e62-trial --target dev \
    --var="catalog=adb_dev" --var="schema=default" \
    --var="runtime_volume=aetheriaforge_runtime" \
    --notebook-params "contract_path=/Volumes/adb_dev/default/aetheriaforge_runtime/contracts/databricks_samples_nyctaxi_trips_forge_contract.yml,catalog=adb_dev,schema=default,evidence_dir=/Volumes/adb_dev/default/aetheriaforge_runtime/evidence"
```

- Start: `2026-04-20 09:07:36` (local) / `16:07:36Z`
- End: `2026-04-20 09:08:37` (local) / `16:08:37Z` (61 s wall)
- Terminal state: `INTERNAL_ERROR / FAILED`
- Run URL: <https://dbc-9cfc36a7-5883.cloud.databricks.com/?o=7474657966305346#job/650093448938396/run/857684359543440>
- Root cause (extracted): `[TABLE_OR_VIEW_NOT_FOUND] The table or view
  'adb_dev.default.trips' cannot be found.` Notebook resolved the source as
  `<widget_catalog>.<widget_schema>.trips` instead of honoring the contract's
  explicit `source.catalog=samples, source.schema=nyctaxi`.

**Investigation finding (root cause):** `notebooks/02_run_forge_pipeline.py`
evaluated `if contract.source_table and catalog.strip()` before the
contract-backed branch, so a non-empty widget catalog silently overrode the
contract's explicit `source.catalog`/`source.schema`. That logic is wrong for
the bootstrap-generated nyctaxi contract and any future cross-catalog read
pattern.

**Fix (commit `5b3a9f4`):** reorder the branches so a contract with fully
specified `source_table + source_catalog + source_schema` wins first. Widget
inputs still drive the target surface and still fill in missing
catalog/schema when the contract only declares `source_table`. Diff in
commit.

### Run 2 (post-fix, SUCCESS) — `775365102945415`

Same CLI as Run 1. Executed after:

1. Editing `notebooks/02_run_forge_pipeline.py` (branch reorder).
2. Re-running `databricks bundle deploy` → workspace files refreshed
   (terraform volume conflict unchanged, non-blocking for the job path).
3. Re-running `make lint typecheck test` → 304 / 304 passing.

Outcome:

- Start: `2026-04-20 09:11:09` (local) / `16:11:09Z`
- End: `2026-04-20 09:12:03Z` (end_time epoch `1776701523644`)
- `setup_duration: 4 s`, `execution_duration: 49 s`, `run_duration: 54 s`
- Terminal state: `TERMINATED / SUCCESS`
- Termination code: `SUCCESS`
- Run URL: <https://dbc-9cfc36a7-5883.cloud.databricks.com/?o=7474657966305346#job/650093448938396/run/775365102945415>
- `overriding_parameters.notebook_params`:

  ```json
  {
    "catalog": "adb_dev",
    "contract_path": "/Volumes/adb_dev/default/aetheriaforge_runtime/contracts/databricks_samples_nyctaxi_trips_forge_contract.yml",
    "evidence_dir": "/Volumes/adb_dev/default/aetheriaforge_runtime/evidence",
    "schema": "default"
  }
  ```
- Creator: `anthony.johnsonii@etherealogic.ai`
- Full JSON run metadata persisted to
  `/tmp/aetheriaforge-live-proof/bundle-run-4.log` on the runner.

## Evidence Artifacts Written to the Live UC Volume (`repo-verified`)

`ls /Volumes/adb_dev/default/aetheriaforge_runtime/evidence/` after the
successful run contained **two new artifacts** produced today, on top of the
four historical ones from 2026-04-04 and 2026-04-10:

| File | Stage |
| --- | --- |
| `forge-evidence-20260420T161146_860571.json` | forge_result (coherence score) |
| `forge-evidence-20260420T161147_363174.json` | pipeline_result (aggregate) |

Inlined excerpt of `forge-evidence-20260420T161147_363174.json`:

```json
{
  "event": "pipeline_result",
  "dataset_name": "databricks_nyctaxi_trips_eval",
  "pipeline_verdict": "PASS",
  "run_at": "2026-04-20T16:11:47.357496+00:00",
  "execution_mode": "contract_backed",
  "source_location": "samples.nyctaxi.trips",
  "target_location": "default.aetheriaforge_nyctaxi_trips_eval",
  "contract_version": "1.0.0",
  "schema_version": "1.0.0",
  "forge_result": {
    "coherence_score": 1.0,
    "verdict": "PASS",
    "threshold": 0.8,
    "records_in": 21932,
    "records_out": 21932,
    "columns_in": ["tpep_pickup_datetime", "tpep_dropoff_datetime",
                    "trip_distance", "fare_amount", "pickup_zip",
                    "dropoff_zip"],
    "columns_out": ["pickup_at", "dropoff_at", "trip_distance_miles",
                     "fare_amount_usd", "pickup_zip", "dropoff_zip"],
    "failure_reason": null
  },
  "enforcement_result": {
    "conformant": {"rows": 21932, "columns": 6},
    "quarantined": {"rows": 0, "columns": 6},
    "coercions_applied": [
      "Coerced column 'pickup_at' from datetime64[ns] to object",
      "Coerced column 'dropoff_at' from datetime64[ns] to object",
      "Coerced column 'pickup_zip' from int32 to int",
      "Coerced column 'dropoff_zip' from int32 to int"
    ],
    "rejection_reasons": []
  }
}
```

`execution_mode: contract_backed` (not `demo` or `unverified`) and
`source_location: samples.nyctaxi.trips` confirm the notebook fix worked:
the live pipeline read from the contract-declared source surface rather
than a widget-forced surface, produced a deterministic Shannon-entropy
coherence score of 1.0 (over the 0.8 silver threshold), and wrote
append-only evidence to the shared UC volume.

## Validation Gates Re-Run Post-Fix (`repo-verified`)

| Gate | Command | Result |
| --- | --- | --- |
| Lint | `make lint` | `All checks passed!` |
| Typecheck | `make typecheck` | `Success: no issues found in 53 source files` |
| Tests | `make test` | `304 passed in 1.67s` |
| Catalog auth | `make bundle-catalog-check CATALOG=adb_dev PROFILE=e62-trial` | pass |
| Bundle validation | `make bundle-validate CATALOG=adb_dev PROFILE=e62-trial` | `Validation OK!` |
| Fresh deploy (workspace files) | `databricks bundle deploy ...` | pass |
| Fresh deploy (terraform resources) | same command | partial — volume conflict on pre-existing orphan; job + app continue to serve |
| Live job run | `databricks bundle run forge_job ...` | `TERMINATED / SUCCESS` (54 s) |

## Residual-Risk Status

**Risk closed:** "the live bundle check proves auth, bundle resolution, and
workspace validation only; it does not prove a fresh deploy or job run in
this session."

- Fresh deploy: **proven** for workspace artifact push (patched notebook is
  live). **Partial** for terraform-managed resources (see next item).
- Fresh job run: **proven** end-to-end — cluster start, notebook install,
  contract load, Spark session, UC read from `samples.nyctaxi.trips`,
  Shannon-entropy coherence scoring, schema enforcement with coercions,
  append-only evidence write to the live UC volume, terminal SUCCESS state.

**New lower-priority residual item flagged for follow-up (not addressed
here):** the managed UC volume `adb_dev.default.aetheriaforge_runtime` is
outside the bundle's Terraform state from a prior bootstrap, causing every
`bundle deploy` to report a terraform error even though workspace files push
cleanly and dependent resources continue to operate. Mitigation options:

1. Back up the two most recent evidence artifacts to an alternate UC
   location, destroy the volume, and let `bundle deploy` recreate it.
2. Bypass Terraform by marking the volume as externally-managed in the
   bundle (requires a config change and verification).
3. Leave as-is; accept the expected terraform error on every deploy as
   long as workspace-file push is the critical path.

Recommend option 1 during a scheduled ops window, with the evidence files
restored to the new volume after re-create. Not blocking day-to-day forge
runs.

## Claim Classification

- `repo-verified`: every commit hash, run ID, timing figure, coherence score,
  row count, column list, volume path, CLI command and result shown above;
  confirmed via `databricks` CLI calls, `pytest`, and repository state.
- `public-page-observed`: pre-resolution Notion state (from the
  15:40:51Z sync record).
- `operator-reported`: none.

## Append-Only Invariants

- This record is new; no prior `report/` artifact is rewritten.
- Evidence artifacts in the UC volume are written by the forge pipeline
  itself and are append-only by design.
- All external claims are traceable either to the repository, to command
  outputs persisted under `/tmp/aetheriaforge-live-proof/`, or to the UC
  volume contents captured at the time of this record.
