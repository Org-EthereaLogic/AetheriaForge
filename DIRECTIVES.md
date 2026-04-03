# ÆtheriaForge Directives

Enforceable repository directives derived from `CONSTITUTION.md`.

## Enforcement Levels

- Critical: blocking requirements enforced by CI or local checks.
- Important: strong requirements that need explicit written rationale if
  bypassed.
- Recommended: recurring practices that keep the workspace reliable.

## Critical Directives

### CRIT-001 — Placeholder Scan Must Pass

No forbidden placeholder markers in specs, .claude, CLAUDE.md, or docs.

### CRIT-002 — Canonical Governance and SDLC Docs Must Exist

The following files are mandatory:

- `AGENTS.md`, `CLAUDE.md`, `CONSTITUTION.md`, `DIRECTIVES.md`
- `specs/AF-PRD-001_Product_Requirements_Document.md`
- `specs/AF-SRS-001_Software_Requirements_Specification.md`
- `specs/AF-SDD-001_Architecture_Blueprint.md`
- `specs/AF-TP-001_Test_Plan.md`
- `specs/AF-IP-001_Implementation_Plan.md`
- `specs/AF-WBS-001_Project_Plan_WBS.md`

### CRIT-003 — No Runtime Dependency on Sibling Projects

`src/aetheriaforge/` must contain first-party code only. No import path may
resolve to DriftSentinel or any sibling project at runtime.

### CRIT-004 — Specs Are Canonical

All authoritative ÆtheriaForge requirements, plans, and architecture claims
live under `specs/`. `docs/` is explanatory and must not override `specs/`.

### CRIT-005 — Evidence-Backed PASS Claims Only

Quality, transformation, and validation PASS claims require explicit evidence
references. No fabricated metrics.

### CRIT-006 — Quality-Control Integration Before Product Code

Codacy, Codecov, and Snyk integration surfaces must be present and documented
before substantive product implementation begins.

### CRIT-007 — CI Must Run Before Merge

`.github/workflows/ci.yml` must run lint, type check, and tests before merge.

### CRIT-008 — No Proprietary UMIF in v1.x

The v1.x codebase must use Shannon entropy exclusively. No QCE, CRE, or T_x
constructs. Entropy engine changes require version bump and traceability update.

## Important Directives

### IMP-001 — Preserve Evidence Artifacts

Do not overwrite or delete append-only evidence under `report/`.

### IMP-002 — Keep Reporting Claim-Safe

When the code or evidence does not support a claim, remove it or mark it as
future scope.

### IMP-003 — Notion Sync Must Be Truthful

Never report a live Notion dashboard update unless it actually occurred. Use
the repo-backed payload fallback when direct mutation is unavailable.

### IMP-004 — Integration Is Optional

DriftSentinel integration must never be required for standalone operation.
The integration layer is inactive by default.

## Recommended Directives

### REC-001 — Prefer Deterministic Defaults

Capture commit hashes, timestamps, and runtime metadata in evidence artifacts.

### REC-002 — Keep Source Files Under 500 Lines

Source-bearing files in `src/aetheriaforge/` and `scripts/` should stay at or
below 500 lines.
