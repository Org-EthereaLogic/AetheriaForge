# integration/

Optional DriftSentinel integration layer for ÆtheriaForge.

## Purpose

When both ÆtheriaForge and DriftSentinel are deployed in the same Databricks
workspace, this module enables cross-product communication:

- **Event emission** — publish transformation events (coherence scores,
  resolution outcomes, schema versions) to a shared directory that
  DriftSentinel can consume.
- **Drift ingestion** — receive drift payloads from DriftSentinel and route
  them into a remediation workflow.

## Standalone Mode

This module is inactive by default. When no bundled-mode configuration is
provided, ÆtheriaForge operates in standalone mode with zero integration
overhead. The `NullEventChannel` is used as the default no-op channel.

## Configuration

Bundled-mode is configured through a YAML file (see
`templates/bundled_mode.yml` for the template) or an `integration` section in
a forge contract.

## Contents

| File | Purpose |
| --- | --- |
| `config.py` | `BundledModeConfig` and configuration discovery |
| `events.py` | `TransformationEvent`, `EventChannel` protocol, `FileEventChannel`, `NullEventChannel` |
| `drift.py` | `DriftReport`, `ColumnDriftReport`, `RemediationAction`, `DriftIngester` |
