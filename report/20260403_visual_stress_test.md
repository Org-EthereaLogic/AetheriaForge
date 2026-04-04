# Visual Stress Test — 2026-04-03

## Scope

- Surface: local Gradio app at `http://127.0.0.1:7860`
- Contracts directory: `/tmp/aetheriaforge_contracts`
- Evidence directory: `/tmp/aetheriaforge_evidence`
- Browser automation: Playwright CLI, desktop and mobile viewports

## Measured Facts

- Local baseline checks passed before and after the app changes:
  - placeholder scan across `specs`, `.claude`, `CLAUDE.md`, `docs`
  - `uv run ruff check .`
  - `uv run mypy src/aetheriaforge tests`
  - `uv run pytest`
- The registry view loaded `8` valid contracts from `/tmp/aetheriaforge_contracts`.
- The status view loaded `5029` evidence artifacts from `/tmp/aetheriaforge_evidence`.
- The evidence row-to-detail navigation worked and auto-opened the Evidence Explorer tab.
- The analytics theme selector worked across at least `Brand` and `Cyberpunk`.
- Mobile rendering remained functional at `390x844`; Gradio collapsed tabs into an overflow menu instead of breaking the layout.

## Issues Found

### 1. Brand theme was not applied in the default render path

- Symptom:
  - The dashboard rendered with Gradio's light default styling instead of the intended midnight/forge palette.
  - Plot labels were low-contrast because the chart font palette was tuned for a dark surface.
- Root cause:
  - `_build_theme()` only set `*_dark` theme tokens, so the active light-mode tokens stayed at Gradio defaults.
- Resolution:
  - Applied the AetheriaForge palette to both the base token and the `*_dark` token for each themed variable.
- Evidence:
  - Before: `output/playwright/registry-desktop.png`
  - After: `output/playwright/registry-desktop-fixed.png`
  - After: `output/playwright/analytics-desktop-fixed.png`

### 2. Analytics refresh had avoidable UI latency from Gradio queue handling

- Symptom:
  - Analytics refresh felt visibly slow under the 5k-artifact evidence set.
- Root cause:
  - Local read-only handlers were going through Gradio's queue, introducing extra queue join/data polling even though the handlers are fast local file reads and chart formatting.
- Resolution:
  - Set `queue=False` and `show_progress="hidden"` on local click/load/change/select handlers.
- Evidence:
  - Before analytics refresh: about `7.35s`
  - After analytics refresh: about `2.33s`
  - After change, network calls switched to direct `POST /gradio_api/run/predict` instead of queue join/data polling.

### 3. Registry startup logs were flooded by malformed-contract warnings

- Symptom:
  - Auto-loading the registry against a directory with many invalid YAML files emitted hundreds of near-identical warning lines.
- Root cause:
  - `DatasetRegistry.from_directory()` logged one warning per malformed file.
- Resolution:
  - Aggregated malformed contract logging into a single summary warning with a bounded preview.
- Evidence:
  - Verified summary output:
    - `WARNING:Skipped 500 malformed contract file(s) in /tmp/aetheriaforge_contracts. Examples: ...`

## Code Changes

- `app/app.py`
  - fixed theme token application
  - disabled Gradio queue/progress overlays for local read-only handlers
- `app/analytics.py`
  - reused `TransformationHistory` instead of maintaining a duplicate analytics-side loader
- `src/aetheriaforge/config/registry.py`
  - summarized malformed contract warnings into one bounded message
- `tests/test_registry.py`
  - added coverage for aggregated malformed-contract warning behavior

## Verification Artifacts

- Desktop screenshots:
  - `output/playwright/registry-desktop.png`
  - `output/playwright/status-desktop.png`
  - `output/playwright/evidence-desktop.png`
  - `output/playwright/analytics-desktop.png`
  - `output/playwright/registry-desktop-fixed.png`
  - `output/playwright/analytics-desktop-fixed.png`
- Mobile screenshots:
  - `output/playwright/registry-mobile.png`
  - `output/playwright/analytics-mobile-fixed.png`

## Interpretation

- The highest-value fixes were the theme correction and queue bypass.
- Backend parsing was already fast in direct Python timing; the user-perceived slowdown was mostly UI transport/render overhead, not raw JSON parsing time.
- No blocking defect remained in the exercised registry, status, evidence explorer, analytics, or mobile-overflow flows after the fixes above.
