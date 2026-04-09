# Bundle Validate Auth Unblock Record — 2026-04-09T16:26:30Z

## Scope

Resolve the external blocker recorded in
`report/2026-04-04T00-35-19Z-brand-ui-verification-correction.md` (line 67),
which stated that `make bundle-validate CATALOG=main` was *"blocked by missing
Databricks default credentials"*. The earlier record is append-only and is not
mutated; this record supersedes that blocker claim with replayable evidence.

## Root Cause

Two independent mistakes in the prior invocation compounded into the apparent
"missing auth" failure:

1. **No `PROFILE=` argument.** `Makefile:26` passes `PROFILE_ARG` only when
   `PROFILE` is set. Without it, the Databricks CLI falls through to the
   `[DEFAULT]` profile in `~/.databrickscfg`, which exists but contains no
   `host`/`auth_type` fields. That empty profile triggers the
   *"default auth: cannot configure default credentials"* error even though a
   valid profile (`e62-trial`) is present in the same config file.
2. **Wrong catalog name.** The prior invocation used `CATALOG=main`, which
   does not exist in the target workspace. The workspace's Unity Catalog
   catalogs are `adb_dev`, `samples`, and `system`. `adb_dev` is the user's
   development catalog.

Nothing is broken in the Makefile, the bundle, or the CLI configuration —
`Makefile:25-26` already exposes `PROFILE` as an override, and
`specs/AF-BI-001_Build_Instructions.md:55-69` already documents the correct
`PROFILE=<profile>` usage pattern. The blocker was an operator-input error,
not an environment gap.

## Corrected Invocation

```bash
make bundle-catalog-check CATALOG=adb_dev PROFILE=e62-trial
make bundle-validate      CATALOG=adb_dev PROFILE=e62-trial
```

Equivalent raw CLI form:

```bash
databricks catalogs get adb_dev -p e62-trial -o json
databricks bundle validate -p e62-trial --target dev --var="catalog=adb_dev"
```

An alternative that removes the need to pass `PROFILE=` on every invocation
is to export `DATABRICKS_CONFIG_PROFILE=e62-trial` in the shell; the Databricks
CLI honors that environment variable for all auth resolution. The
`[__settings__] default_profile = e62-trial` entry in `~/.databrickscfg` is
**not** honored by `databricks bundle validate` (confirmed empirically on
Databricks CLI v0.295.0), so the env var or the explicit `-p` flag is required.

## Replayable Evidence

### 1. Databricks CLI and profile state

```
$ databricks --version
Databricks CLI v0.295.0

$ databricks auth describe -p e62-trial
Host: https://dbc-9cfc36a7-5883.cloud.databricks.com
User: anthony.johnsonii@etherealogic.ai
Authenticated with: databricks-cli
-----
Current configuration:
  ✓ host: https://dbc-9cfc36a7-5883.cloud.databricks.com (from /Users/etherealogic-2/.databrickscfg config file)
  ✓ profile: e62-trial (from --profile flag)
  ✓ auth_type: databricks-cli (from /Users/etherealogic-2/.databrickscfg config file)
```

### 2. Negative reproduction — confirm the prior failure mode

```
$ databricks bundle validate --target dev --var="catalog=main"
Error: failed during request visitor: default auth: cannot configure default
credentials, please check https://docs.databricks.com/en/dev-tools/auth.html#databricks-client-unified-authentication
to configure credentials for your preferred authentication method

Name: aetheriaforge
Target: dev

Found 1 error
```

This matches the symptom recorded in the 2026-04-04 blocker report and
confirms the root cause is the empty `[DEFAULT]` profile fallback, not a
missing or expired credential.

### 3. Catalog existence check — PASS

```
$ make bundle-catalog-check CATALOG=adb_dev PROFILE=e62-trial
databricks catalogs get "${CATALOG:?Set CATALOG}" -p e62-trial -o json
{
  "browse_only": false,
  "catalog_type": "MANAGED_CATALOG",
  "comment": "ADB MVP development environment for Bronze/Silver/Gold demo",
  "full_name": "adb_dev",
  "isolation_mode": "OPEN",
  "metastore_id": "1028ccdc-a4f5-4a1f-9421-198861b234dd",
  "name": "adb_dev",
  "owner": "anthony.johnsonii@etherealogic.ai",
  "securable_type": "CATALOG",
  ...
}
```

### 4. Bundle validation — PASS

```
$ make bundle-validate CATALOG=adb_dev PROFILE=e62-trial
databricks bundle validate -p e62-trial --target dev --var="catalog=${BUNDLE_VAR_catalog:-${CATALOG:?Set CATALOG or BUNDLE_VAR_catalog}}"
Name: aetheriaforge
Target: dev
Workspace:
  User: anthony.johnsonii@etherealogic.ai
  Path: /Workspace/Users/anthony.johnsonii@etherealogic.ai/.bundle/aetheriaforge/dev

Validation OK!
```

## Scope of the PASS

Consistent with `specs/AF-BI-001_Build_Instructions.md:68-69`, `Validation OK!`
proves only bundle syntax, auth, and resource resolution against the explicit
catalog input. It does **not** prove `databricks bundle deploy` or
`databricks bundle run forge_job` — those remain separate gates under sections
5 and 6 of the Build Instructions and are outside the scope of this unblock
record.

## Superseded Claim

The entry at
`report/2026-04-04T00-35-19Z-brand-ui-verification-correction.md:67`
— *"`make bundle-validate CATALOG=main` | blocked by missing Databricks
default credentials"* — and its matching External Blockers paragraph are
superseded by this record. Both the auth and the bundle validation paths are
functional when invoked with the correct `PROFILE=e62-trial` and
`CATALOG=adb_dev` inputs. The append-only 2026-04-04 file remains unchanged.
