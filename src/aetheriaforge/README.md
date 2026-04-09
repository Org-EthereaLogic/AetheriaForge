# src/aetheriaforge

First-party ÆtheriaForge product code.

## Subpackages

| Package | Purpose |
| --- | --- |
| `ingest/` | Enterprise file ingestion (CSV, Parquet, JSON, Excel, XML, ORC, Avro, fixed-width) |
| `forge/` | Contract-driven transformation and coherence scoring (Shannon entropy v1.x) |
| `resolution/` | Exact-match cross-source entity resolution |
| `temporal/` | `latest_wins` temporal reconciliation and conflict recording |
| `schema/` | Schema-contract loading and schema enforcement |
| `evidence/` | Append-only transformation artifact writing |
| `orchestration/` | Workflow sequencing for the forge pipeline |
| `config/` | Forge contract and policy configuration |
| `integration/` | Optional DriftSentinel event and drift follow-up interface (standalone by default) |
