# ÆtheriaForge — Notion Dashboard Sync Policy

| Field | Value |
| --- | --- |
| Document | notion_dashboard_sync.md |
| Version | 1.0 |
| Status | Active |
| Date | 2026-04-03 |

## Target Page

| Field | Value |
| --- | --- |
| Title | AetheriaForge UMIF Data Quality Drift Foundry |
| Page ID | 33af5d74-5418-42d8-bf9d-a6bdeeb88956 |
| URL | https://www.notion.so/AetheriaForge-UMIF-Data-Quality-Drift-Foundry-33af5d74541842d8bf9da6bdeeb88956 |

## Sync Policy

- Notion is an external coordination surface only — never a runtime dependency.
- Only the page identified above may be updated unless the operator explicitly
  supplies an alternative target.
- The page must be read before any write to confirm the target.
- All sync content must reflect repo-verified state. No claims from inference
  or memory alone.
- Every sync run produces an append-only evidence record under `report/` before
  finalizing. Evidence records are never rewritten.
- If direct mutation is unavailable, a publish-ready payload is prepared locally
  and the live page is marked unchanged.

## Claim Classification

Every claim in a sync payload must be classified as one of:

| Classification | Meaning |
| --- | --- |
| `repo-verified` | Claim is directly supported by current repo state (file exists, command output, etc.) |
| `public-page-observed` | Claim was read from the live Notion page during the sync run |
| `operator-reported` | Claim was supplied by the operator in this session; not independently verified |

## Sync Record Format

Sync records are written to `report/YYYY-MM-DDTHH-MM-SS-notion-sync-record.md`
and contain:

- current implementation phase and milestone status (repo-verified)
- latest validation status from lint, typecheck, tests, and deployment checks
  (repo-verified)
- current branch, commit hash, and timestamp (repo-verified)
- open risks, blockers, and next actions (repo-verified or operator-reported)
- links to newly created evidence under `report/` (repo-verified)
- Notion sync mode and outcome
