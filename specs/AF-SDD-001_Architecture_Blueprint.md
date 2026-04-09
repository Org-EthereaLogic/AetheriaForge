# AF-SDD-001: ÆtheriaForge Architecture Blueprint

| Field | Value |
| --- | --- |
| Document ID | AF-SDD-001 |
| Version | 1.0 |
| Status | Draft |
| Author | Anthony Johnson |
| Date | 2026-04-03 |

## 1. Repository Taxonomy

```text
aetheriaforge/
  README.md, AGENTS.md, CLAUDE.md, CONSTITUTION.md, DIRECTIVES.md
  SECURITY.md, CONTRIBUTING.md, LICENSE
  specs/
  docs/
  .claude/ (commands/, agents/, hooks/, settings.json)
  adws/
  report/
  databricks.yml
  app/
  scripts/
  resources/
  notebooks/
  templates/
  src/aetheriaforge/
  tests/
  assets/
```

## 2. Layer Model

### Agentic Layer

- `specs/` — canonical SDLC contract
- `.claude/commands/` — 21 reusable task prompts
- `.claude/agents/` — 5 specialized subagent definitions
- `.claude/hooks/` — Claude Code hook handlers
- `CLAUDE.md` — quick-reference operational guide
- `adws/` — reserved for AI Developer Workflows
- `report/` — append-only evidence surface

### Application Layer

- `src/aetheriaforge/ingest/` — enterprise file ingestion (CSV, Parquet, JSON, Excel, XML, ORC, Avro, etc.)
- `src/aetheriaforge/forge/` — contract-driven transformation and coherence scoring
- `src/aetheriaforge/resolution/` — exact-match cross-source entity resolution
- `src/aetheriaforge/temporal/` — `latest_wins` temporal reconciliation and conflict logic
- `src/aetheriaforge/schema/` — schema-contract loading and schema enforcement
- `src/aetheriaforge/evidence/` — append-only transformation artifact writing
- `src/aetheriaforge/orchestration/` — workflow sequencing for the forge pipeline
- `src/aetheriaforge/config/` — forge contract and policy configuration
- `app/` — Databricks App UI for read-only operator review
- `scripts/` — operational helpers for bundle-backed app deployment
- `resources/` — bundle pipeline and job definitions
- `notebooks/` — onboarding and review surfaces
- `templates/` — forge contract, resolution policy, and schema contract templates

### Integration Layer (Optional)

- `src/aetheriaforge/integration/` — reserved for DriftSentinel event interface
- Event emission: publish transformation events (coherence scores, resolution
  outcomes, schema versions) to a channel DriftSentinel can consume
- Drift ingestion: receive drift payloads from DriftSentinel and route into
  evidence-backed follow-up actions
- This layer is inactive by default; enabled only when bundled mode is configured

## 3. Module Responsibilities

| Module | Primary Job | Medallion Layer |
| --- | --- | --- |
| `ingest/` | Enterprise file format ingestion | Pre-Bronze (file → DataFrame) |
| `forge/` | Coherence-scored transformations | Bronze → Silver |
| `resolution/` | Exact-match cross-source entity reconciliation | Silver |
| `temporal/` | `latest_wins` temporal record reconciliation | Silver |
| `schema/` | Schema-contract transformation and enforcement | Silver → Gold |
| `evidence/` | Append-only transformation artifacts | All layers |
| `orchestration/` | Pipeline sequencing across modules | All layers |
| `config/` | Contract and policy management | All layers |

## 4. Control Flow

1. Register dataset and forge contract
2. Ingest source files (CSV, Parquet, JSON, Excel, XML, ORC, Avro, fixed-width)
3. Load source data from Bronze layer
4. Execute schema-contract transformation and optional schema enforcement
5. Score the transformed output with Shannon entropy
6. Run optional exact-match entity resolution across configured source mappings
7. Run optional `latest_wins` temporal reconciliation for time-inconsistent records
8. Write forged Silver-ready output to target surface
9. Write append-only transformation evidence
10. Emit transformation event (if bundled mode is active)
11. Review outcomes through notebooks and the operator dashboard

## 5. Entropy Engine Architecture

### v1.x — Shannon Entropy (Current Build Target)

The v1.x coherence scoring engine uses Shannon entropy to measure information
loss across transformations. Each transformation step produces a coherence
score between 0.0 and 1.0 representing the ratio of information preserved.
For schema-contract runs, the scorer evaluates each forged target column
against its declared source lineage and excludes undeclared source columns from
the denominator. Renamed targets therefore retain credit for preserved
information, while lossy transforms such as rounding still reduce the score.

Layer thresholds:
- Bronze: tolerates higher entropy (≥ 0.5)
- Silver: measurable quality threshold (≥ 0.75)
- Gold: near-zero coherence loss (≥ 0.95)

### v3.0 — UMIF Entropy (Future Roadmap)

Reserved for proprietary QCE, CRE, and T_x constructs. No v3.0 material
exists in the v1.x repository. The migration path and performance comparison
methodology will be defined in a separate controlled document.

## 6. Methodology Precedence

1. DriftSentinel (primary sibling reference for scaffold and governance pattern)
2. FailLens_Core
3. E62_Live_Databricks_Bronze_execution
4. E63_Natural-fault_Bronze_validation
5. ADWS_PRO
6. Supporting examples: agentic_coding_template, themegpt-v2.0, chapter repos
