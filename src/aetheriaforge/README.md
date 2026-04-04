# src/aetheriaforge

First-party ÆtheriaForge product code.

## Subpackages

| Package | Purpose |
| --- | --- |
| `ingest/` | Enterprise file ingestion (CSV, Parquet, JSON, Excel, XML, ORC, Avro, fixed-width) |
| `forge/` | Coherence-scored transformation engine (Shannon entropy v1.x) |
| `resolution/` | Cross-source entity resolution |
| `temporal/` | Temporal reconciliation and merge logic |
| `schema/` | Schema enforcement and evolution management |
| `evidence/` | Append-only transformation artifact writing |
| `orchestration/` | Workflow sequencing for the forge pipeline |
| `config/` | Forge contract and policy configuration |
| `integration/` | Optional DriftSentinel event and drift interface (standalone by default) |
