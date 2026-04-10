# CLAUDE.md — ÆtheriaForge Product Repository Quick Reference

ÆtheriaForge is the intelligent data transformation engine in the EthereaLogic
Databricks Suite. It actively transforms, reconciles, and forges clean data
across the Medallion architecture with coherence-scored evidence for every
operation. Designed to operate standalone or integrate with DriftSentinel for
a complete governed pipeline.

## Methodology Precedence

When prior repository patterns conflict, use this precedence:

1. `DriftSentinel` (primary sibling for governance and scaffold pattern)
2. `FailLens_Core`
3. `E62_Live_Databricks_Bronze_execution`
4. `E63_Natural-fault_Bronze_validation`
5. `ADWS_PRO`
6. supporting examples from `agentic_coding_template`, `themegpt-v2.0`, and
   the older Databricks chapter repositories

## Command Shortlist

| Command | Use |
| --- | --- |
| `make sync` | Install runtime and development dependencies |
| `make lint` | Lint the repository with Ruff |
| `make typecheck` | Type-check with mypy |
| `make test` | Run the pytest suite |
| `make coverage` | Run tests with coverage reporting |
| `make bundle-catalog-check CATALOG=<catalog> [PROFILE=<profile>]` | Prove the selected Unity Catalog catalog exists for the current Databricks auth context |
| `make bundle-validate CATALOG=<catalog> [PROFILE=<profile>] [SCHEMA=<schema>] [VOLUME=<volume>]` | Validate the Databricks Asset Bundle against explicit catalog/schema/volume inputs |
| `make app-deploy CATALOG=<catalog> [PROFILE=<profile>] [SCHEMA=<schema>] [VOLUME=<volume>]` | Deploy the AetheriaForge Databricks App from bundle-uploaded source |
| `make bootstrap CATALOG=<catalog> [PROFILE=<profile>] [SCHEMA=<schema>] [VOLUME=<volume>] [SAMPLE=nyctaxi]` | One-command Databricks onboarding: verify auth, deploy bundle, create volume, upload templates, start app |

### Core Workflow Commands (21 total)

| Command | Use |
| --- | --- |
| `/prime` | Orient to the repository before acting |
| `/start` | Set up local environment and verify project is functional |
| `/plan` | Create or update structured plans in `specs/` |
| `/implement` | Execute scoped work under the canonical contract |
| `/review` | Review work against requirements and architecture |
| `/verify` | Independently verify claims with evidence |
| `/test` | Run the full validation suite |
| `/audit` | Full governance and canonical docs audit |
| `/feature` | Plan a new feature with scope and placement check |
| `/bug` | Plan a focused bug fix with root cause analysis |
| `/patch` | Create a minimal targeted patch plan |
| `/chore` | Execute low-risk maintenance under governance |
| `/classify_issue` | Classify a GitHub issue as chore, bug, or feature |
| `/generate_branch_name` | Generate a valid branch name from an issue |
| `/commit` | Produce a scoped conventional commit |
| `/pull-request` | Create a GitHub PR after all checks pass |
| `/git` | Safe git operations with protected-branch enforcement |
| `/doc-maintain` | Audit and repair documentation drift |
| `/document` | Generate implementation documentation in `specs/` |
| `/cleanup_workspace` | Dry-run or execute safe workspace cleanup |
| `/sync` | Audit docs, validate, and handle Notion dashboard sync |

## Agent Surface

| Agent | Role |
| --- | --- |
| `lead-software-engineer` | Production implementation and spec-to-code translation |
| `sdlc-technical-writer` | Canonical SDLC documentation and traceability |
| `test-automator` | Test strategy, validation, and evidence QA |
| `python-pro` | Typed Python, packaging, uv workflows, PySpark integration |
| `ux-delight-specialist` | Gradio dashboard UI polish, layout, data presentation, empty states |

## External Coordination

| Surface | Target |
| --- | --- |
| Notion dashboard | [AetheriaForge UMIF Data Quality Drift Foundry](https://www.notion.so/33af5d74541842d8bf9da6bdeeb88956) |
| Sync policy | `docs/notion_dashboard_sync.md` |

## File Map

Every directory contains a `README.md` describing its contents.

| Path | Purpose |
| --- | --- |
| `specs/` | Canonical SDLC documents |
| `docs/` | Explanatory docs, deployment guide, Notion sync policy |
| `.claude/` | Claude Code configuration root |
| `.claude/commands/` | 21 reusable command prompts |
| `.claude/agents/` | 5 specialized subagent definitions |
| `.claude/hooks/` | Claude Code hook handlers and session logging |
| `.claude/settings.json` | Claude Code plugin configuration |
| `src/` | Top-level source directory (src-layout) |
| `src/aetheriaforge/` | First-party product code |
| `src/aetheriaforge/ingest/` | Enterprise file ingestion (CSV, Parquet, JSON, Excel, XML, ORC, Avro, etc.) |
| `src/aetheriaforge/forge/` | Coherence-scored transformation engine |
| `src/aetheriaforge/resolution/` | Cross-source entity resolution |
| `src/aetheriaforge/temporal/` | Temporal reconciliation and merge logic |
| `src/aetheriaforge/schema/` | Schema enforcement and evolution management |
| `src/aetheriaforge/evidence/` | Append-only transformation artifact writing |
| `src/aetheriaforge/orchestration/` | Workflow sequencing for the forge pipeline |
| `src/aetheriaforge/config/` | Forge contract and policy configuration |
| `src/aetheriaforge/integration/` | Optional DriftSentinel event and drift interface |
| `app/` | Databricks App UI (Gradio) — operator dashboard for forge review |
| `assets/` | Project brand assets |
| `notebooks/` | Databricks onboarding, execution, and review notebooks |
| `resources/` | Databricks Asset Bundle pipeline, job, and app resource definitions |
| `templates/` | Forge contract, resolution policy, and schema contract templates |
| `scripts/` | Operational helper scripts |
| `tests/` | Product test suite |
| `adws/` | Reserved for AI Developer Workflows |
| `report/` | Append-only evidence artifacts |

## Working Rules

- `specs/` is canonical over `docs/` when they diverge.
- `report/` is append-only — never overwrite or delete evidence.
- No runtime dependency on DriftSentinel or sibling project clones.
- Codacy, Codecov, and Snyk are pre-implementation gates.
- Notion is an external coordination surface only, never a runtime dependency.
- Separate measured facts from interpretation.
- No PASS claims without replayable evidence.
- v1.x uses Shannon entropy only — no proprietary UMIF material in this repo.
