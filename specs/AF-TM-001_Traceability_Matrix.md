# AF-TM-001: ÆtheriaForge Traceability Matrix

| Field | Value |
| --- | --- |
| Document ID | AF-TM-001 |
| Version | 1.1 |
| Status | Draft |
| Author | Anthony Johnson |
| Date | 2026-04-04 |

| PRD Requirement | SRS Requirement | Spec Surface | Verification Surface |
| --- | --- | --- | --- |
| AF-FR-001 | AF-SR-001 | PRD, SDD | repo taxonomy, CLAUDE.md, specs/ |
| AF-FR-002 | AF-SR-010 | PRD, SRS | databricks.yml, resources/, bundle validation |
| AF-FR-003 | AF-SR-009 | PRD, SRS | notebooks, manual import path |
| AF-FR-004 | AF-SR-006 | PRD, SRS | templates/, config loaders, registration notebook |
| AF-FR-005 | AF-SR-002 | PRD, SDD | src/aetheriaforge/forge/, coherence scoring tests |
| AF-FR-006 | AF-SR-002 | PRD, SDD | src/aetheriaforge/forge/, transformation tests |
| AF-FR-007 | AF-SR-003 | PRD, SDD | src/aetheriaforge/resolution/, resolution tests |
| AF-FR-008 | AF-SR-004 | PRD, SDD | src/aetheriaforge/temporal/, temporal tests |
| AF-FR-009 | AF-SR-005 | PRD, SDD | src/aetheriaforge/schema/, schema enforcement tests |
| AF-FR-010 | AF-SR-008 | PRD, TP | evidence writer tests, evidence artifact inspection |
| AF-FR-011 | AF-SR-007 | PRD, TP | quarantine tests, failure reason preservation |
| AF-FR-012 | AF-SR-008, AF-SR-011 | PRD, TP | deterministic demo paths and integration tests |
| AF-FR-013 | AF-SR-012 | PRD, SRS | integration/event emission tests |
| AF-FR-014 | AF-SR-013 | PRD, SRS | integration/drift ingestion tests |
| AF-FR-015 | AF-SR-014 | PRD, SRS, SCMP | .codacy/, codecov.yaml, .snyk, secret-name docs |
| AF-FR-016 | AF-SR-015 | PRD, SRS, SCMP | docs/notion_dashboard_sync.md, /sync command |
| AF-FR-017 | AF-SR-009 | PRD, SRS | app/, operator dashboard tests |
| AF-FR-018 | AF-SR-016 | PRD, SRS, SDD, TP | src/aetheriaforge/ingest/, file ingestion tests |
| AF-NFR-001 | AF-SNFR-002, AF-SNFR-006 | PRD, SRS, TP | report/, transformation evidence |
| AF-NFR-002 | AF-SNFR-001 | PRD, SRS | append-only evidence writer and replay tests |
| AF-NFR-003 | AF-SNFR-003 | PRD, SRS | missing-field failure tests, blocked status checks |
| AF-NFR-004 | AF-SNFR-005 | PRD, SRS | Free Edition notebook path, workspace scheduling |
| AF-NFR-005 | AF-SNFR-004 | PRD, SDD, SCMP | specs/, .claude/, adws/, report/ scaffold |
| AF-NFR-006 | AF-SNFR-003 | PRD, SRS | blocked transformation tests |
| AF-NFR-007 | AF-SNFR-007 | PRD, SRS | secret scan, .gitignore, CI checks |
| AF-NFR-008 | AF-SNFR-008 | PRD, SRS, WBS | documented pre-coding gate |
| AF-NFR-009 | AF-SNFR-009 | PRD, SRS, TP | non-blocking Notion sync rules |
| AF-NFR-010 | AF-SNFR-010 | PRD, SRS | no UMIF material in v1.x codebase |
| AF-NFR-011 | AF-SNFR-011 | PRD, SRS, TP | standalone mode tests, no DriftSentinel dependency |
