# app

Databricks App UI (Gradio) — read-only operator dashboard for ÆtheriaForge.

## Contents

| File | Purpose |
| --- | --- |
| `app.py` | Main Gradio Blocks application with four tabs |
| `analytics.py` | Plotly chart builders for the Analytics tab |
| `app.yaml` | Databricks App runtime configuration |
| `requirements.txt` | App-specific Python dependencies |
| `__init__.py` | Package marker |

## Tabs

1. **Forge Registry** — browse registered datasets and contract configuration
2. **Transformation Status** — filter and summarize recent forge pipeline runs
3. **Evidence Explorer** — inspect full evidence artifact JSON
4. **Analytics** — verdict distribution, coherence trends, and daily volume

## Running Locally

```bash
uv sync --group app
gradio app/app.py
```

## Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `CONTRACTS_DIR` | `/tmp/aetheriaforge_contracts` | Directory containing YAML forge contracts |
| `EVIDENCE_DIR` | `/tmp/aetheriaforge_evidence` | Directory containing evidence JSON artifacts |
