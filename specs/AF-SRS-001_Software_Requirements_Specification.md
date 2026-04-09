# AF-SRS-001: ÆtheriaForge Software Requirements Specification

| Field | Value |
| --- | --- |
| Document ID | AF-SRS-001 |
| Version | 1.1 |
| Status | Draft |
| Author | Anthony Johnson |
| Date | 2026-04-04 |

## 1. Functional Requirements

| ID | Traces to | Requirement |
| --- | --- | --- |
| AF-SR-001 | AF-FR-001 | Single repository layout with product code, deployment assets, notebooks, specs, and agent-layer scaffolding |
| AF-SR-002 | AF-FR-005, AF-FR-006 | First-party forge engine that transforms Bronze records into Silver-ready structures with Shannon entropy coherence scoring |
| AF-SR-003 | AF-FR-007 | First-party entity resolution engine that normalizes identifiers across multiple source systems using configured exact key matching and ambiguity controls in v1.x |
| AF-SR-004 | AF-FR-008 | First-party temporal reconciliation engine that applies deterministic `latest_wins` selection with duplicate-timestamp conflict detection in v1.x |
| AF-SR-005 | AF-FR-009 | Schema enforcement layer that validates and coerces records against versioned schema contracts while recording the applied contract version |
| AF-SR-006 | AF-FR-004 | Declarative forge registration through YAML contracts specifying source, target, schema, resolution rules, and coherence thresholds |
| AF-SR-007 | AF-FR-011 | Downstream-safe output surface separate from raw and quarantined surfaces; explicit failure reasons preserved |
| AF-SR-008 | AF-FR-010, AF-FR-012 | Persist coherence scores, resolution outcomes, temporal merge decisions, schema coercions, and transformation metadata as append-only evidence |
| AF-SR-009 | AF-FR-003, AF-FR-017 | Onboarding, execution, evidence-review notebooks and operator dashboard |
| AF-SR-010 | AF-FR-002 | Bundle deployment path and manual import path |
| AF-SR-011 | AF-FR-012 | Deterministic demo path for local and workspace validation |
| AF-SR-012 | AF-FR-013 | Event emission interface publishing transformation events (coherence scores, resolution outcomes, schema versions applied) to a lightweight channel consumable by DriftSentinel |
| AF-SR-013 | AF-FR-014 | Drift payload ingestion interface that receives drift reports from DriftSentinel and routes them into evidence-backed follow-up actions |
| AF-SR-014 | AF-FR-015 | Pre-implementation Codacy, Codecov, and Snyk setup |
| AF-SR-015 | AF-FR-016 | Evidence-backed Notion dashboard sync policy with payload fallback |
| AF-SR-016 | AF-FR-018 | File ingestion module that reads CSV, TSV, Parquet, JSON, JSONL, Excel, XML, ORC, Avro, and fixed-width files into DataFrames with format detection, reader options, and optional evidence writing |

## 2. Non-Functional Requirements

| ID | Traces to | Requirement |
| --- | --- | --- |
| AF-SNFR-001 | AF-NFR-002 | Evidence shall be append-only and audit-friendly |
| AF-SNFR-002 | AF-NFR-001 | Release claims bounded by measured proof from this repository |
| AF-SNFR-003 | AF-NFR-006 | Missing evidence fields or failed coherence checks force explicit failure or blocked status |
| AF-SNFR-004 | AF-NFR-005 | Separation between canonical specs, explanatory docs, agent prompts, and evidence |
| AF-SNFR-005 | AF-NFR-004 | Notebook-first for Free Edition with clean path to paid-workspace scheduling |
| AF-SNFR-006 | AF-NFR-001 | No runtime dependency on DriftSentinel or sibling project clones |
| AF-SNFR-007 | AF-NFR-007 | No secrets or hard-coded customer data in repository content |
| AF-SNFR-008 | AF-NFR-008 | No coding before quality-control preflight gate is satisfied |
| AF-SNFR-009 | AF-NFR-009 | Notion sync is non-blocking and truthful |
| AF-SNFR-010 | AF-NFR-010 | v1.x contains no proprietary UMIF material; Shannon entropy only |
| AF-SNFR-011 | AF-NFR-011 | DriftSentinel integration is always optional; standalone is the default path |

## 3. External Interfaces

- Databricks CLI and Asset Bundles
- Databricks notebooks and workspace import
- Unity Catalog (catalogs, schemas, tables, volumes)
- Local Python tooling for packaging and tests
- DriftSentinel event interface (optional, bundled mode only)
- Notion dashboard as external coordination surface

## 4. Assumptions

- Free Edition has strict limits on apps, pipelines, jobs
- Marketplace provider operations require a paid workspace with Unity Catalog
- GitHub Actions secrets: `CODECOV_TOKEN` (preferred) or
  `CODECOV_PROJECT_TOKEN` for backward compatibility, plus
  `SNYK_PROJECT_TOKEN`; `CODACY_PROJECT_TOKEN` is only required if the project
  switches to Codacy client-side upload mode
- DriftSentinel integration requires both products deployed in the same
  workspace or connected through an event bridge
