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

## Branding

- Header logos are read from `app/brand/` (copies of the canonical brand
  variants) when present and fall back to a text-only header otherwise.
- Analytics exposes five color themes: `Brand`, `Traffic Light`,
  `Colorblind Safe`, `Cyberpunk`, and `Pastel`.

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
| `CONTRACTS_DIR` | `~/.aetheriaforge/contracts` | Directory containing YAML forge contracts |
| `EVIDENCE_DIR` | `~/.aetheriaforge/evidence` | Directory containing evidence JSON artifacts |
