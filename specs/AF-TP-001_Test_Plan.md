# AF-TP-001: ÆtheriaForge Test Plan

| Field | Value |
| --- | --- |
| Document ID | AF-TP-001 |
| Version | 1.1 |
| Status | Draft |
| Author | Anthony Johnson |
| Date | 2026-04-04 |

## 1. Scaffold Verification

- Canonical `specs/AF-*.md` suite exists
- `.claude/commands/`, `.claude/agents/`, `.claude/hooks/` exist
- Quality-control integration files present (`.codacy/`, `codecov.yaml`, `.snyk`)
- No forbidden stub markers in canonical surfaces

## 2. Forge Engine Verification

- Unit tests for coherence scoring with Shannon entropy
- Transformation correctness: Bronze input → Silver output matches contract
- Threshold enforcement: transformations below layer threshold produce FAIL
- Coherence score determinism: same input always produces same score
- Evidence-write tests proving append-only behavior

## 3. Resolution Engine Verification

- Unit tests for entity matching across configurable rules
- Cross-source resolution: records with different IDs for the same entity merge
- Ambiguous match handling: configurable behavior (fail, skip, best-match)
- Resolution evidence: every match decision is recorded

## 4. Temporal Engine Verification

- Unit tests for CDC, SCD Type 2, and batch merge logic
- Temporal conflict detection: overlapping records produce explicit conflicts
- Merge determinism: same inputs always produce same merge result
- Temporal evidence: merge decisions and conflict resolutions recorded

## 5. Schema Enforcement Verification

- Unit tests for schema validation, coercion, and evolution
- Contract versioning: older evidence retains the contract version active at time of forging
- Evolution: schema changes produce new contract versions, not retroactive mutation
- Rejection evidence: non-conformant records quarantined with explicit reasons

## 6. File Ingestion Verification

- Unit tests for format detection from file extensions
- Reader tests for each supported format: CSV, TSV, Parquet, JSON, JSONL, Excel, XML, ORC, Avro, fixed-width
- Format override: explicit format parameter bypasses extension detection
- Reader options: delimiter, encoding, sheet name, and other format-specific options pass through
- Error handling: missing files, malformed content, and unsupported extensions produce explicit error results
- Evidence writing: ingestion artifacts record file path, format, record count, and column list
- IngestResult API: `ok` property, `as_dict()` JSON-safe serialization

## 7. Integration Verification

- Event emission: transformation events reach the configured channel
- Drift ingestion: DriftSentinel payloads route into remediation workflow
- Standalone mode: integration disabled by default, no errors when DriftSentinel absent
- Bundle resources and notebook orchestration tests

## 8. Deployment Verification

- Databricks workspace validation for both deployment paths
- Configuration tests for forge contract registration and policy loading
- Notebook import path operates without bundle
- Operator dashboard regression coverage verifies logo-asset availability,
  analytics theme options, and brand asset manifest integrity

## 9. Exit Criteria

No phase is complete until tests agree with canonical specs, measured outputs
support claimed verdicts, and evidence is replayable.
