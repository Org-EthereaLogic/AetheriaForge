# AF-IP-004: Phase 4 — Multi-Dataset Hardening

| Field | Value |
| --- | --- |
| Document ID | AF-IP-004 |
| Version | 1.0 |
| Status | Draft |
| Author | Anthony Johnson |
| Date | 2026-04-03 |
| Parent | AF-IP-001 Phase 4 |

## Objective

Harden ÆtheriaForge so that a single installation operates multiple datasets
safely. Each dataset has its own versioned forge contract. Transformation
evidence is queryable by dataset, time range, and verdict. The orchestration
pipeline processes N registered datasets in a single batch run.

## Pre-conditions

- Phase 3 complete (commit 9f3c7a4)
- 58 tests passing, lint/typecheck clean
- ForgeContract, ForgePipeline, EvidenceWriter, and all engine modules exist

## Deliverables

### 1. DatasetRegistry (`src/aetheriaforge/config/registry.py`)

A registry that manages multiple ForgeContracts with version awareness.

| Capability | Method |
| --- | --- |
| Register a contract | `register(contract)` |
| Get latest contract by dataset name | `get(name)` |
| Get a specific version | `get(name, version)` |
| List all registered dataset names | `list_datasets()` |
| List all versions of a dataset | `list_versions(name)` |
| Load all contracts from a directory | `load_directory(path)` |
| Count of registered contracts | `len(registry)` |

Design constraints:
- Immutable entries: once registered, a name+version pair cannot be overwritten
- `get(name)` returns the latest version using semantic version ordering
- `register()` raises `ValueError` on duplicate name+version
- Backed by an in-memory dict; directory loading is a convenience classmethod

### 2. TransformationHistory (`src/aetheriaforge/evidence/history.py`)

Query interface over the evidence directory for transformation results.

| Capability | Method |
| --- | --- |
| List all evidence records | `list_all()` |
| Filter by dataset name | `query(dataset_name=...)` |
| Filter by verdict | `query(verdict=...)` |
| Filter by time range | `query(after=..., before=...)` |
| Combined filters | `query(dataset_name=..., verdict=..., after=..., before=...)` |
| Summary statistics | `summary()` |

Design constraints:
- Reads evidence JSON files from the evidence directory (same as EvidenceWriter)
- Returns list of dicts sorted by timestamp descending (newest first)
- `summary()` returns counts grouped by dataset and verdict
- Read-only — never modifies evidence files
- Tolerant of malformed files (skip with warning, don't crash)

### 3. ForgeRunner (`src/aetheriaforge/orchestration/runner.py`)

Batch pipeline execution across registered datasets.

| Capability | Method |
| --- | --- |
| Run all provided datasets | `run(inputs)` |
| Run a single dataset by name | `run_one(name, input)` |

Data model:
- `DatasetInput` dataclass: bundles `source_df`, `forged_df`, and optional
  `schema_columns`, `secondary_df`, `resolution_policy`, `temporal_config`,
  `target_layer` for a single dataset
- `BatchResult` dataclass: maps dataset names to `PipelineResult`, with
  a `batch_verdict` (worst of all pipeline verdicts) and `run_at` timestamp

Design constraints:
- `run()` accepts `dict[str, DatasetInput]` — only datasets present in both
  the registry and the inputs dict are processed
- Skipped datasets (in registry but not in inputs, or vice versa) are recorded
  in `BatchResult.skipped`
- Each dataset runs through `ForgePipeline` with the contract from the registry
- Evidence is written per-dataset (shared EvidenceWriter)

### 4. Tests

| File | Covers |
| --- | --- |
| `tests/test_registry.py` | Registry CRUD, versioning, directory loading, duplicate rejection |
| `tests/test_history.py` | Evidence query, filtering, summary, malformed file tolerance |
| `tests/test_runner.py` | Batch run, single run, skip tracking, verdict aggregation |

## File Map

| Path | Action |
| --- | --- |
| `src/aetheriaforge/config/registry.py` | Create |
| `src/aetheriaforge/config/__init__.py` | Update — export DatasetRegistry |
| `src/aetheriaforge/evidence/history.py` | Create |
| `src/aetheriaforge/evidence/__init__.py` | Update — export TransformationHistory |
| `src/aetheriaforge/orchestration/runner.py` | Create |
| `src/aetheriaforge/orchestration/__init__.py` | Update — export ForgeRunner, BatchResult, DatasetInput |
| `tests/test_registry.py` | Create |
| `tests/test_history.py` | Create |
| `tests/test_runner.py` | Create |

## Acceptance Criteria

1. `DatasetRegistry` registers, retrieves, and lists contracts with version
   ordering; rejects duplicates; loads from a YAML directory
2. `TransformationHistory` queries evidence files with dataset, verdict, and
   time-range filters; produces summary statistics; tolerates malformed files
3. `ForgeRunner` processes multiple datasets in one batch; aggregates verdicts;
   tracks skipped datasets; writes per-dataset evidence
4. All new tests pass
5. `uv run ruff check .` — clean
6. `uv run mypy src/aetheriaforge tests` — clean
7. `uv run pytest` — all pass (58 existing + new Phase 4 tests)
8. Placeholder scan — clean

## Out of Scope

- Persistent on-disk registry (in-memory only for Phase 4)
- Parallel/concurrent dataset processing (sequential is sufficient)
- Forge contract migration tooling (manual version bumps)
- App or notebook updates (Phase 5)
