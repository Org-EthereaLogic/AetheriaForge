---
description: Audit docs, validate, commit & push, and sync the configured AetheriaForge public Notion AI page using append-only evidence.
---

# sync

Audit documentation, update for drift, commit changes, push to GitHub, and sync
project state with the configured public Notion AI page.

## Variables

scope: $ARGUMENTS
notion_page_title: AetheriaForge UMIF Data Quality Drift Foundry
notion_page_url: https://www.notion.so/AetheriaForge-UMIF-Data-Quality-Drift-Foundry-33af5d74541842d8bf9da6bdeeb88956?source=copy_link
notion_page_id: 33af5d74-5418-42d8-bf9d-a6bdeeb88956

## Workflow

### Phase 1: Documentation Audit & Update

- Run the `/doc-maintain` workflow internally
- Check for cross-reference leaks (stale project names, outdated URLs,
  references to other projects)
- Update living artifacts (`docs/` numbered documents)
- Specs in `specs/` are versioned — never modify existing decisions without a
  version bump

### Phase 2: Validate

- Run `git diff --check` to verify no whitespace errors
- Run `make lint` to ensure linting passes
- Run `make typecheck` to ensure type-checking passes
- Run `make test` to ensure tests pass
- Run `make bundle-catalog-check CATALOG=<existing_uc_catalog> PROFILE=<profile>`
  and `make bundle-validate CATALOG=<existing_uc_catalog> PROFILE=<profile>`
  when Databricks CLI authentication is configured and a real catalog is
  available.

### Phase 3: Commit & Push

- Clean up any remaining untracked files, then push or sync them to the GitHub
  remote following industry standards and best practices for commit conventions.
- Safety: Never force push. Never skip hooks.

### Phase 4: Notion Sync

Sync project state between the local codebase and the configured public Notion
AI page.

**Target page:**

- Title: `AetheriaForge UMIF Data Quality Drift Foundry`
- URL: `https://www.notion.so/AetheriaForge-UMIF-Data-Quality-Drift-Foundry-33af5d74541842d8bf9da6bdeeb88956?source=copy_link`
- Page ID: `33af5d74-5418-42d8-bf9d-a6bdeeb88956`

**Sync requirements:**

- Read the public page first to confirm the target before making any change
- Sync only this page unless the operator explicitly supplies another target
- Prepare a concise update that reflects repo-verified state only:
  - current implementation phase and milestone status
  - latest validation status from lint, typecheck, tests, and deployment checks
  - current branch, commit, and timestamp
  - open risks, blockers, and next actions
  - links or references to newly created repo evidence under `report/`
- If authenticated edit access is available, update the live Notion page and
  capture what changed in the sync record
- If direct mutation is unavailable, prepare a publish-ready Notion payload in
  the sync record and mark the live page as unchanged
- Never claim the page was updated if only a local payload or recommendation was
  produced

**Evidence record:**

1. Create a new timestamped record under `report/` before finalizing the sync:
   `report/YYYY-MM-DDTHH-MM-SS-notion-sync-record.md`
2. Never rewrite an earlier sync artifact
3. Classify every external claim as `repo-verified`, `public-page-observed`,
   or `operator-reported`

### Phase 5: Report

```text
=== Sync Report ===

### Documentation
- Files audited: N
- Files updated: N
- Drift issues found: N
- Drift issues fixed: N

### Validation
- Lint: pass/fail
- Typecheck: pass/fail
- Tests: pass/fail

### Git
- Commit: {hash} {message}
- Push: success/failure
- Sync record: {report path}

### Notion
- Target page: AetheriaForge UMIF Data Quality Drift Foundry
- URL: https://www.notion.so/AetheriaForge-UMIF-Data-Quality-Drift-Foundry-33af5d74541842d8bf9da6bdeeb88956?source=copy_link
- Sync mode: direct-update/payload-only/no-access/failure
- Project page: updated/unchanged
- Tasks created: N
- Tasks updated: N
```
