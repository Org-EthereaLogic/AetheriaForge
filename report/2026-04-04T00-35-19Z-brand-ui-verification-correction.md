# Brand/UI Verification Correction Record — 2026-04-04T00:35:19Z

## Scope

Correct the unsupported claims recorded in
`report/2026-04-04T00-25-07-notion-sync-record.md` without mutating that
append-only record.

## Superseded Claims

The earlier record stated:

- the AetheriaForge brand package contained `28` assets
- the package mirrored DriftSentinel's structure

Those statements are superseded by the evidence below.

## Corrected Facts

- `assets/aetheriaforge-brand-system/` contains `25` generated assets across
  `source/`, `icons/`, `variants/`, `favicons/`, and `social/`
- the directory contains `27` files total when `README.md` and
  `generate_brand_assets.py` are included
- the package follows the same top-level bucket pattern used by DriftSentinel
  for repo consistency, but it is not a full mirror of that package because it
  does not contain a `marketplace/` subtree
- the Databricks App does consume the brand logos from
  `assets/aetheriaforge-brand-system/variants/` when those files are present
- the Analytics tab exposes five themes:
  `Brand`, `Traffic Light`, `Colorblind Safe`, `Cyberpunk`, and `Pastel`

## Repo Evidence

- `assets/aetheriaforge-brand-system/README.md` now documents the corrected
  inventory and bounded parity statement
- `assets/README.md` now states that asset presence alone is not deployment
  proof, while also documenting that the app reads logo variants from this
  surface when present
- `app/README.md` now documents the logo-header behavior and five analytics
  themes
- `specs/AF-IP-005_Phase5_Databricks_App.md` now lists all five analytics theme
  options in the canonical Phase 5 spec

## Added Regression Coverage

- `tests/test_brand_assets.py`
  - verifies required brand files exist
  - verifies generated inventory counts: `3 + 4 + 6 + 9 + 3 = 25`
  - verifies total file count is `27`
  - verifies exported raster dimensions
  - verifies `site.webmanifest` metadata matches exported icons
- `tests/test_app.py`
  - verifies `_get_logo_uris()` returns base64 PNG data URIs
  - verifies `build_analytics_data()` skips malformed JSON
  - verifies all five analytics themes build figures
- `tests/test_registry.py`
  - verifies malformed YAML files are skipped during registry directory loading

## Verification Commands

| Command | Result |
| --- | --- |
| `PATTERN='TO''DO\|FIX''ME\|TB''D\|PLACE''HOLDER'; rg -n "$PATTERN" specs .claude CLAUDE.md docs` | no matches |
| `uv run ruff check .` | PASS |
| `uv run mypy src/aetheriaforge tests` | PASS — `39 source files` |
| `uv run pytest` | PASS — `161 passed` |
| `make bundle-validate CATALOG=main` | blocked by missing Databricks default credentials |

## External Blockers

- Databricks bundle validation could not complete locally because the CLI had no
  configured default credentials for workspace authentication. This is an
  environment/authentication issue, not a code or bundle syntax failure.
