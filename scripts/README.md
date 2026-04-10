# scripts

Operational helper scripts for deployment and data generation.

## Contents

| Script | Purpose |
| --- | --- |
| `bootstrap_databricks.py` | One-command Databricks onboarding: verify auth, deploy bundle, create volume, upload templates, start app, trigger job |
| `deploy_databricks_app.py` | Incremental Databricks App deploy from bundle-uploaded source |
| `generate_real_world_stress_fixtures.py` | Generate realistic stress test fixtures |
| `run_large_scale_stress_test.py` | Run large-scale stress tests against the forge engine |
