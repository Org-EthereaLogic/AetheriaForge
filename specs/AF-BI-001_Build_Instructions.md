# AF-BI-001: ÆtheriaForge Build Instructions

| Field | Value |
| --- | --- |
| Document ID | AF-BI-001 |
| Version | 1.0 |
| Status | Draft |
| Author | Anthony Johnson |
| Date | 2026-04-03 |

## 1. Pre-Implementation Quality-Control Gate

Before substantive product code, verify:

- `.codacy/README.md` exists
- `codecov.yaml` exists
- `.snyk` exists
- `.github/workflows/ci.yml` wires:
  - Codecov upload via `CODECOV_TOKEN` (preferred) or `CODECOV_PROJECT_TOKEN`
    for backward compatibility
  - Snyk auth via `SNYK_PROJECT_TOKEN`
  - Codacy CI analysis via `codacy/codacy-analysis-cli-action`

Codacy has two valid CI modes:

1. Default analysis mode: no Codacy token required, results appear in the GitHub
   Actions log and the workflow fails on detected issues.
2. Client-side upload mode: requires a Codacy token plus enabling `Run analysis on your build server` in Codacy repository settings before CI uploads will succeed.

The current repository workflow uses default analysis mode to avoid depending on
that optional external Codacy setting.

## 2. Local Build

```bash
uv sync --all-groups
uv run ruff check .
uv run mypy src/aetheriaforge tests
uv run pytest
```

## 3. Bootstrap (Recommended First-Time Setup)

The bootstrap command is the single entry point for first-time Databricks
onboarding. It verifies authentication and catalog access, deploys the Asset
Bundle (which creates the runtime volume), uploads contract templates to the
volume, starts the Databricks App, and optionally triggers the forge job.

```bash
make bootstrap CATALOG=<existing_uc_catalog> PROFILE=<profile>
```

With a sample dataset:

```bash
make bootstrap CATALOG=<existing_uc_catalog> PROFILE=<profile> SAMPLE=nyctaxi
```

With a non-default schema or runtime volume:

```bash
make bootstrap CATALOG=<existing_uc_catalog> PROFILE=<profile> SCHEMA=<schema> VOLUME=<volume>
```

Or run the script directly:

```bash
uv run --group databricks python scripts/bootstrap_databricks.py \
    --catalog <existing_uc_catalog> --profile <profile> --sample nyctaxi
```

Prerequisites:
- Databricks CLI authenticated via `databricks auth login --host <workspace-url>`
- `databricks-sdk` installed via `uv sync --group databricks`
- An existing Unity Catalog catalog and schema in the target workspace

Expected result: the bundle deploys, the runtime volume is created, templates
are uploaded, the app starts, and the script prints the app URL, evidence
path, and contracts path.

## 4. Catalog Access Check

Before bundle validation, prove the selected Unity Catalog catalog exists in
the intended workspace:

```bash
make bundle-catalog-check CATALOG=<existing_uc_catalog> PROFILE=<profile>
databricks catalogs get <existing_uc_catalog> -p <profile>
```

Expected result: the CLI returns catalog metadata for the exact catalog you
plan to pass into the bundle.

## 5. Bundle Validation

Authenticate the Databricks CLI through `.databrickscfg`,
`DATABRICKS_CONFIG_PROFILE`, or `DATABRICKS_*` environment variables, then
run. Pass `SCHEMA` and `VOLUME` when you are not using the bundle defaults
(`default` and `aetheriaforge_runtime`):

```bash
make bundle-validate CATALOG=<existing_uc_catalog> PROFILE=<profile>
databricks bundle validate -p <profile> --target dev --var="catalog=<existing_uc_catalog>"
```

Expected result: the bundle validates, resolves `resources/*.yml`, and
requires an explicit existing Unity Catalog catalog instead of relying on
an unsafe hard-coded default. `Validation OK!` proves bundle/auth/resource
resolution only; it does not prove deploy or job execution.

## 6. Deployment Activation

Deploy and run with the same catalog selection:

```bash
databricks bundle deploy -p <profile> --target dev --var="catalog=<existing_uc_catalog>"
databricks bundle run forge_job -p <profile> --target dev --var="catalog=<existing_uc_catalog>"
```

Expected result: the bundle deploys Databricks jobs and pipelines into the
workspace and the forge job terminates successfully when the package and
catalog inputs are valid.

## 7. App Deployment

Deploy the Gradio operator dashboard as a Databricks App:

```bash
make app-deploy CATALOG=<existing_uc_catalog> PROFILE=<profile>
```

Or run the deploy script directly:

```bash
python scripts/deploy_databricks_app.py --catalog <existing_uc_catalog> --profile <profile>
```

Expected result: the app deploys, compute becomes ACTIVE, and the script
prints the app URL. The dashboard provides read-only access to the forge
registry, transformation evidence, and analytics charts.

For local development:

```bash
uv sync --group app
gradio app/app.py
```

## 8. Manual Workspace Import

Upload the `notebooks/` directory to a Databricks workspace to run the package
from the deployed bundle files when available, falling back to GitHub for
standalone imports.

## 9. Governance Guard Check

```bash
uv run pytest tests/test_governance_guards.py -q
```

Expected result: executable and bundle surfaces contain no banned scaffold
markers, `databricks.yml` includes `resources/*.yml`, and the bundle does not
encode Databricks auth interpolation.

## 10. Canonical Placeholder Scan

```bash
PATTERN='TO''DO|FIX''ME|TB''D|PLACE''HOLDER'; rg -n "$PATTERN" specs .claude CLAUDE.md docs
```

Expected result: no matches.
