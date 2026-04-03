# AF-IP-006: Phase 6 — DriftSentinel Integration Layer

| Field | Value |
| --- | --- |
| Document ID | AF-IP-006 |
| Version | 1.0 |
| Status | Draft |
| Author | Anthony Johnson |
| Date | 2026-04-03 |
| Parent | AF-IP-001 Phase 6 |

## Objective

Add an optional integration layer so ÆtheriaForge can exchange transformation
events and drift payloads with DriftSentinel when both products are deployed in
the same Databricks workspace. Standalone mode remains the default — integration
is opt-in through bundled-mode configuration.

## Pre-conditions

- Phase 5 complete (commit ed0cfa2)
- 117 tests passing, lint/typecheck clean
- All forge, resolution, temporal, schema, evidence, orchestration, config, and
  app modules exist
- Architecture blueprint reserves `src/aetheriaforge/integration/` for this layer

## Design Constraints

- No runtime dependency on DriftSentinel (AF-NFR-011 / AF-SNFR-011)
- ÆtheriaForge defines its own data shapes — no DriftSentinel type imports
- Standalone mode is always the default; integration is opt-in
- v1.x uses file-based event exchange (JSON files in shared directories)
- v1.x remediation is re-score/flag only, not auto-fix

## Deliverables

### 1. Event Emission Interface (WBS 3.1)

`src/aetheriaforge/integration/events.py`

| Type | Purpose |
| --- | --- |
| `TransformationEvent` | Frozen dataclass — event payload with coherence score, verdict, resolution outcome, schema version |
| `EventChannel` | Protocol with `emit(event) -> None` |
| `FileEventChannel` | Writes JSON events to a shared directory (append-only) |
| `NullEventChannel` | No-op channel for standalone mode |

Factory: `TransformationEvent.from_pipeline_result(result, contract)` extracts
fields from the existing `PipelineResult.as_dict()` payload.

### 2. Drift Payload Ingestion (WBS 3.2)

`src/aetheriaforge/integration/drift.py`

| Type | Purpose |
| --- | --- |
| `DriftReport` | Frozen dataclass — inbound drift payload parsed from JSON |
| `ColumnDriftReport` | Frozen dataclass — per-column drift detail |
| `RemediationAction` | Frozen dataclass — routing result: `re_score` / `flag_only` / `skip` |
| `DriftIngester` | Reads drift files, routes into remediation |

Routing logic:
- Registered dataset + WARN/FAIL gate verdict → `re_score`
- Registered dataset + PASS gate verdict → `flag_only`
- Unknown dataset → `skip`

Processed drift files are renamed to `.processed` to prevent re-ingestion.

### 3. Bundled-Mode Configuration (WBS 3.3)

`src/aetheriaforge/integration/config.py`

| Type | Purpose |
| --- | --- |
| `BundledModeConfig` | Frozen dataclass: `enabled`, `events_dir`, `drift_dir`, `auto_ingest` |
| `discover_bundled_config()` | Resolve config from YAML file or contract dict; defaults to disabled |

Template: `templates/bundled_mode.yml`

### 4. Orchestration Wire-Up

| File | Change |
| --- | --- |
| `src/aetheriaforge/orchestration/pipeline.py` | Optional `event_channel` param; emit after evidence write |
| `src/aetheriaforge/orchestration/runner.py` | Optional `event_channel` param; pass through to pipeline |

Integration types use `TYPE_CHECKING` guard — zero runtime import in standalone
mode. The deferred import inside `if self.event_channel is not None:` ensures
the integration module is never loaded when disabled.

### 5. Integration Tests (WBS 3.4)

`tests/test_integration.py`

| Category | Key assertions |
| --- | --- |
| Config | from_dict, from_yaml, disabled factory, discover with no sources |
| Events | TransformationEvent factory, FileEventChannel writes JSON, NullEventChannel no-op |
| Pipeline wire-up | Event emitted when channel provided, no event when None |
| Runner wire-up | Events emitted for each processed dataset |
| Drift shapes | DriftReport.from_dict, frozen, defaults |
| Ingestion routing | re_score on WARN/FAIL, flag_only on PASS, skip on unknown |
| Evidence | Remediation actions written when evidence_writer provided |
| File management | Processed files renamed to .processed |
| Standalone mode | Pipeline and runner run without errors when event_channel is None |

## Exit Criteria

- All new integration types are frozen dataclasses
- Event emission reaches the configured directory after pipeline execution
- Drift payloads route correctly for all three paths
- Standalone mode produces zero integration errors
- All existing 117 tests continue to pass unchanged
- New integration tests pass
- Lint and typecheck pass
