# AF-SCMP-001: ÆtheriaForge Software Configuration Management Plan

| Field | Value |
| --- | --- |
| Document ID | AF-SCMP-001 |
| Version | 1.0 |
| Status | Draft |
| Author | Anthony Johnson |
| Date | 2026-04-03 |

## 1. Repository Model

- Primary branch: `main`
- Feature work: short-lived feature and fix branches

## 2. Controlled Items

| Item Type | Location |
| --- | --- |
| Product code | `src/aetheriaforge/` |
| Tests | `tests/` |
| Deployment assets | `databricks.yml`, `resources/`, `notebooks/`, `templates/` |
| Canonical SDLC docs | `specs/` |
| Narrative docs | `docs/` |
| Claude commands, agents, hooks | `.claude/` |
| Workflow orchestration | `adws/` |
| Evidence artifacts | `report/` |
| Quality-control integration | `.github/`, `.codacy/`, `codecov.yaml`, `.snyk` |
| External coordination | Notion dashboard URL and repo-backed sync payloads |

## 3. Change Rules

- `specs/` is canonical and version-controlled
- `docs/` must not override `specs/`
- Evidence artifacts are append-only
- Secrets must never be committed
- Codacy, Codecov, and Snyk are pre-implementation gates
- Repository-secret names are documented; token values are never stored
- Notion IDs must never be invented; only user-supplied targets are used
- No proprietary UMIF material in v1.x; entropy engine changes require version bump
- DriftSentinel integration changes require traceability update to AF-TM-001
