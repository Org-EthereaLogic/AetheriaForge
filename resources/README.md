# resources

Databricks Asset Bundle pipeline, job, app, and volume resource definitions.

## Contents

| File | Purpose |
| --- | --- |
| `forge_job.yml` | Forge pipeline job — runs `02_run_forge_pipeline.py` notebook |
| `aetheriaforge_app.yml` | Gradio operator dashboard — deployed from `app/` directory |
| `runtime_volume.yml` | Bundle-managed Unity Catalog volume for shared contracts and evidence |
