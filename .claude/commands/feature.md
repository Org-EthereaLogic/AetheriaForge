# feature

Plan a new ÆtheriaForge feature: scope it, decide placement, produce a specs/
plan file.

## Variables

issue_or_description: $ARGUMENTS

## Instructions

- Parse `issue_or_description` for issue details or use as a plain description
- Research the codebase to understand existing patterns and architecture
- Create the plan in `specs/` with filename: `feature-{descriptive-name}.md`
- Use RELATIVE paths only

## Boundary Check

Before writing the plan, decide placement:

- This repo: forge engine, entity resolution, temporal reconciliation, schema
  enforcement, coherence scoring, evidence surfaces, orchestration, notebooks,
  bundle configuration, forge contracts, DriftSentinel integration layer
- Not this repo: DriftSentinel internals, drift detection, publication gating,
  chapter-specific logic, UI/frontend scaffolding

If the feature belongs elsewhere, stop and explain why.

## Validation Commands

- stub-marker scan
- `uv run ruff check .`
- `uv run pytest`
- `make bundle-validate CATALOG=<existing_uc_catalog> PROFILE=<profile>` (if
  bundle assets changed and Databricks auth plus catalog access are available)

## Report

Return exclusively the path to the plan file created.
