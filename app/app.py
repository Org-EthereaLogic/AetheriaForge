"""AetheriaForge Databricks App — read-only operator dashboard.

Provides four views over existing AetheriaForge package surfaces:
1. Forge Registry — browse registered datasets and contract configuration
2. Transformation Status — filter and summarize recent forge pipeline runs
3. Evidence Explorer — inspect full evidence artifact detail
4. Analytics — verdict distribution, coherence trends, and daily volume

This app never writes evidence, modifies the registry, or executes pipelines.
"""

from __future__ import annotations

import json
import os
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import gradio as gr
except ImportError:  # allow test imports without gradio installed
    gr = None  # type: ignore[assignment]

from aetheriaforge.config.registry import DatasetRegistry
from aetheriaforge.evidence.history import TransformationHistory

CONTRACTS_DIR = os.environ.get("CONTRACTS_DIR", "/tmp/aetheriaforge_contracts")
EVIDENCE_DIR = os.environ.get("EVIDENCE_DIR", "/tmp/aetheriaforge_evidence")

# -- Brand palette (AetheriaForge) -------------------------------------------

_MIDNIGHT = "#0A0E1A"
_DEEP_FORGE = "#111827"
_CLOUD = "#E8ECF4"
_FORGE_VIOLET = "#8B5CF6"
_FORGE_INDIGO = "#6366F1"
_EMBER_AMBER = "#F59E0B"
_TRUST_EMERALD = "#10B981"
_ALERT_ROSE = "#F43F5E"
_SLATE_MUTED = "#94A3B8"
_VERDICT_CIRCLES = {"PASS": "\U0001f7e2 PASS", "FAIL": "\U0001f534 FAIL", "WARN": "\U0001f7e1 WARN"}

_ASSETS = Path(__file__).parent.parent / "assets" / "aetheriaforge-brand-system"


def _get_logo_uris() -> tuple[str | None, str | None]:
    """Encode the light and dark brand logos as base64 data URIs."""
    import base64

    def _b64(path: Path) -> str | None:
        if not path.is_file():
            return None
        return f"data:image/png;base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"

    return (
        _b64(_ASSETS / "variants" / "logo-light.png"),
        _b64(_ASSETS / "variants" / "logo-dark.png"),
    )


# -- Helpers -----------------------------------------------------------------

def _fmt_timestamp(raw: str) -> str:
    """Convert ISO 8601 to compact human-readable form: 'Apr 02, 14:40 UTC'."""
    if not raw:
        return ""
    try:
        dt = datetime.fromisoformat(raw).astimezone(timezone.utc)
        return dt.strftime("%b %d, %H:%M UTC")
    except (ValueError, TypeError):
        return raw


def _build_summary_line(rows: list[list[str]]) -> str:
    """Build a Markdown summary with total count and verdict breakdown."""
    if not rows or (len(rows) == 1 and "no artifacts" in rows[0][0].lower()):
        return ""
    total = len(rows)
    counts: dict[str, int] = {"PASS": 0, "FAIL": 0, "WARN": 0}
    other = 0
    for row in rows:
        raw = (row[2].strip() if len(row) > 2 else "")
        v = raw.split()[-1].upper() if raw else ""
        if v in counts:
            counts[v] += 1
        else:
            other += 1
    parts = [f"**{total} artifact{'s' if total != 1 else ''}**"]
    if counts["PASS"]:
        parts.append(f"\U0001f7e2 PASS: {counts['PASS']}")
    if counts["WARN"]:
        parts.append(f"\U0001f7e1 WARN: {counts['WARN']}")
    if counts["FAIL"]:
        parts.append(f"\U0001f534 FAIL: {counts['FAIL']}")
    if other:
        parts.append(f"other: {other}")
    return "  |  ".join(parts)


# -- Registry helpers --------------------------------------------------------

def load_registry_table(contracts_dir: str) -> list[list[str]]:
    """Load all forge contracts from a directory into table rows."""
    cdir = contracts_dir.strip() or CONTRACTS_DIR
    path = Path(cdir)
    if not path.is_dir():
        return [["(no contracts directory found)", "", "", "", "", ""]]
    try:
        registry = DatasetRegistry.from_directory(path)
    except Exception as exc:  # noqa: BLE001
        return [[f"(error: {exc})", "", "", "", "", ""]]
    datasets = registry.list_datasets()
    if not datasets:
        return [["(no datasets registered)", "", "", "", "", ""]]
    rows: list[list[str]] = []
    for name in datasets:
        for version in registry.list_versions(name):
            contract = registry.get(name, version)
            source = f"{contract.source_schema}.{contract.source_table}"
            target = f"{contract.target_schema}.{contract.target_table}"
            rows.append([
                name,
                version,
                source,
                target,
                contract.coherence.engine,
                f"{contract.coherence.silver_min:.2f}",
            ])
    return rows


def _registry_status_text(rows: list[list[str]]) -> str:
    """Return a Markdown status line for the registry result."""
    if not rows:
        return ""
    first = rows[0][0]
    if "no contracts directory" in first:
        return (
            "No contracts directory found at the path above. "
            "Create YAML forge contracts and reload."
        )
    if "no datasets" in first:
        return "Directory loaded but contains no YAML contracts. Add a forge contract and reload."
    if first.startswith("(error"):
        return f"Contracts could not be parsed. Check file contents. Detail: `{first}`"
    count = len(rows)
    return f"**{count} contract{'s' if count != 1 else ''} registered**"


# -- Evidence helpers --------------------------------------------------------

def query_evidence(
    evidence_dir: str,
    dataset_name: str,
    verdict: str,
    date_from: str,
    date_to: str,
) -> list[list[str]]:
    """Query evidence and return rows for the summary table."""
    edir = evidence_dir.strip() or EVIDENCE_DIR
    history = TransformationHistory(Path(edir))

    after = None
    before = None
    if date_from.strip():
        try:
            after = datetime.fromisoformat(date_from.strip())
        except ValueError:
            pass
    if date_to.strip():
        try:
            before = datetime.fromisoformat(date_to.strip())
        except ValueError:
            pass

    try:
        results = history.query(
            dataset_name=dataset_name.strip() or None,
            verdict=verdict.strip() or None,
            after=after,
            before=before,
        )
    except Exception as exc:  # noqa: BLE001
        return [[f"(error: {exc})", "", "", "", "", ""]]

    if not results:
        return [["(no artifacts found)", "", "", "", "", ""]]

    rows: list[list[str]] = []
    for artifact in results:
        filename = Path(artifact.get("_evidence_path", "")).name
        ds_name = artifact.get("dataset_name", "")
        v = artifact.get("pipeline_verdict", artifact.get("verdict", ""))
        verdict_display = _VERDICT_CIRCLES.get(str(v).upper(), str(v))
        score = artifact.get("forge_result", {}).get("coherence_score", "")
        if isinstance(score, float):
            score = f"{score:.4f}"
        records_in = artifact.get("forge_result", {}).get("records_in", "")
        records_out = artifact.get("forge_result", {}).get("records_out", "")
        record_str = f"{records_in} \u2192 {records_out}" if records_in != "" else ""
        ts = artifact.get("run_at", artifact.get("forged_at", ""))
        rows.append([
            filename,
            str(ds_name),
            verdict_display,
            str(score),
            record_str,
            _fmt_timestamp(str(ts)),
        ])
    return rows


def load_artifact_detail(evidence_dir: str, filename: str) -> str:
    """Load and return the full JSON of an evidence artifact."""
    fname = filename.strip()
    if not fname:
        return "(select an artifact filename)"
    edir = evidence_dir.strip() or EVIDENCE_DIR
    path = Path(edir) / fname
    if not path.is_file():
        return f"(file not found: {fname})"
    try:
        data = json.loads(path.read_text())
        return json.dumps(data, indent=2, default=str)
    except (json.JSONDecodeError, OSError) as exc:
        return f"(error reading artifact: {exc})"


def load_artifact_meta(evidence_dir: str, filename: str) -> str:
    """Return a Markdown one-line metadata summary for an evidence artifact."""
    fname = filename.strip()
    if not fname:
        return "_Enter an artifact filename above and click Load Artifact._"
    edir = evidence_dir.strip() or EVIDENCE_DIR
    path = Path(edir) / fname
    if not path.is_file():
        return f"_File not found: `{fname}`_"
    try:
        data = json.loads(path.read_text())
        ds_name = data.get("dataset_name", "\u2014")
        raw_verdict = str(
            data.get("pipeline_verdict", data.get("verdict", ""))
        ).strip().upper()
        verdict = _VERDICT_CIRCLES.get(raw_verdict, raw_verdict) or "\u2014"
        score = data.get("forge_result", {}).get("coherence_score", "")
        score_str = f"{score:.4f}" if isinstance(score, float) else str(score) or "\u2014"
        ts = data.get("run_at", data.get("forged_at", ""))
        return (
            f"**Dataset:** `{ds_name}`  "
            f"**Verdict:** {verdict}  "
            f"**Coherence:** `{score_str}`  "
            f"**Timestamp:** {_fmt_timestamp(str(ts)) or chr(8212)}"
        )
    except (json.JSONDecodeError, OSError) as exc:
        return f"_Error reading artifact: {exc}_"


# -- Theme -------------------------------------------------------------------

def _build_theme():  # type: ignore[no-untyped-def]
    """Return an AetheriaForge-branded Gradio theme."""
    violet_hue = gr.themes.Color(
        c50="#F5F3FF", c100="#EDE9FE", c200="#DDD6FE", c300="#C4B5FD",
        c400="#A78BFA", c500=_FORGE_VIOLET, c600="#7C3AED", c700="#6D28D9",
        c800="#5B21B6", c900="#4C1D95", c950="#2E1065",
    )
    slate_hue = gr.themes.Color(
        c50="#F8FAFC", c100="#F1F5F9", c200="#E2E8F0", c300="#CBD5E1",
        c400=_SLATE_MUTED, c500="#64748B", c600="#475569", c700="#334155",
        c800=_DEEP_FORGE, c900=_MIDNIGHT, c950="#050816",
    )
    pairs = {
        "body_background_fill": _MIDNIGHT, "body_text_color": _CLOUD,
        "block_background_fill": _DEEP_FORGE, "block_border_color": "#1E293B",
        "block_label_text_color": _SLATE_MUTED,
        "input_background_fill": "#1E293B", "input_border_color": "#334155",
        "button_primary_background_fill": _FORGE_VIOLET,
        "button_primary_text_color": "#FFFFFF",
        "button_primary_background_fill_hover": "#7C3AED",
        "table_even_background_fill": _DEEP_FORGE,
        "table_odd_background_fill": "#1E293B", "table_border_color": "#1E293B",
        "border_color_primary": _FORGE_VIOLET, "link_text_color": _FORGE_VIOLET,
        "code_background_fill": "#050816",
    }
    theme_args: dict[str, str] = {}
    for k, v in pairs.items():
        theme_args[k] = v
        theme_args[f"{k}_dark"] = v
    return gr.themes.Base(
        primary_hue=violet_hue, neutral_hue=slate_hue,
        font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
        font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "ui-monospace", "monospace"],
    ).set(**theme_args)


_AF_CSS = """
    .af-summary { color: var(--body-text-color-subdued); font-size: 0.88em; margin-top: 4px; }
    .af-tab-desc { color: var(--body-text-color-subdued); font-size: 0.9em; margin-bottom: 12px; }
    .af-empty-state { text-align: center; padding: 24px 16px;
        font-size: 0.95em; color: var(--body-text-color-subdued); }
    #af-logo-dark { display: none !important; }
    .dark #af-logo-dark, :root.dark #af-logo-dark, body.dark #af-logo-dark { display: block !important; }
    .dark #af-logo-light, :root.dark #af-logo-light, body.dark #af-logo-light { display: none !important; }
    .table-container { overflow-x: auto !important; }
    .disable_click { overflow: visible !important; }
"""


# -- App builder -------------------------------------------------------------

def build_app():  # type: ignore[no-untyped-def]
    """Construct the Gradio Blocks app with four tabs."""
    blocks_kwargs: dict[str, Any] = {
        "title": "\u00c6theriaForge",
        "theme": _build_theme(),
        "css": _AF_CSS,
    }

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        ctx = gr.Blocks(**blocks_kwargs)  # type: ignore[arg-type]

    with ctx as app:
        # ---- Header ----
        logo_light_uri, logo_dark_uri = _get_logo_uris()
        if logo_light_uri and logo_dark_uri:
            gr.HTML(
                '<div style="display:flex;align-items:center;gap:16px;'
                'padding:12px 0 8px 0;">'
                f'<img id="af-logo-light" src="{logo_light_uri}"'
                ' alt="\u00c6theriaForge" style="height:64px;width:auto;" />'
                f'<img id="af-logo-dark" src="{logo_dark_uri}"'
                ' alt="\u00c6theriaForge" style="height:64px;width:auto;" />'
                '<span style="color:var(--body-text-color-subdued);'
                'font-size:0.85em;">'
                'Read-only operator dashboard \u2014 forge registry,'
                ' transformation evidence, analytics</span>'
                '</div>'
            )
        else:
            gr.Markdown(
                "## \u2692\ufe0f \u00c6theriaForge\n"
                f"<span style='color:{_SLATE_MUTED};font-size:0.85em;'>"
                "Read-only operator dashboard \u2014 forge registry,"
                " transformation evidence, analytics</span>",
            )

        # ---- Tabs ----
        with gr.Tabs(elem_id="tabs") as tabs:

            # ---- Tab 1: Forge Registry ----
            with gr.Tab("Forge Registry", id="registry"):
                gr.Markdown(
                    "Browse all datasets registered via forge contracts. "
                    "Each row shows the dataset name, version, source/target location, "
                    "and coherence configuration.",
                    elem_classes=["af-tab-desc"],
                )
                with gr.Row():
                    reg_path = gr.Textbox(
                        label="Contracts Directory", value=CONTRACTS_DIR, scale=4,
                    )
                    reg_btn = gr.Button("Load Registry", variant="primary", scale=1)
                reg_status = gr.Markdown(
                    "_Click Load Registry to fetch the current forge contracts._",
                    elem_classes=["af-summary", "af-empty-state"],
                )
                reg_table = gr.Dataframe(
                    headers=[
                        "Dataset", "Version", "Source", "Target", "Engine", "Silver Min",
                    ],
                    column_widths=["15%", "8%", "27%", "27%", "10%", "13%"],
                    interactive=False, wrap=True,
                )

                def _load_registry_with_status(
                    rp: str,
                ) -> tuple[list[list[str]], str]:
                    rows = load_registry_table(rp)
                    return rows, _registry_status_text(rows)

                reg_btn.click(
                    fn=_load_registry_with_status,
                    inputs=[reg_path],
                    outputs=[reg_table, reg_status],
                    queue=False,
                    show_progress="hidden",
                )

            # ---- Tab 2: Transformation Status ----
            with gr.Tab("Transformation Status", id="status"):
                gr.Markdown(
                    "Filter and inspect recent forge pipeline evidence. "
                    "Each row is one pipeline run artifact from the evidence directory.",
                    elem_classes=["af-tab-desc"],
                )
                with gr.Row():
                    ev_dir = gr.Textbox(
                        label="Evidence Directory", value=EVIDENCE_DIR, scale=4,
                    )
                    query_btn = gr.Button("Query", variant="primary", scale=1)
                with gr.Accordion("Filters", open=False):
                    with gr.Row():
                        ds_filter = gr.Textbox(
                            label="Dataset Name", value="",
                            placeholder="e.g. customer_orders",
                        )
                        verdict_filter = gr.Dropdown(
                            label="Verdict",
                            choices=["", "PASS", "WARN", "FAIL"], value="",
                        )
                    with gr.Row():
                        from_filter = gr.Textbox(
                            label="Date From", value="", placeholder="YYYY-MM-DD",
                        )
                        to_filter = gr.Textbox(
                            label="Date To", value="", placeholder="YYYY-MM-DD",
                        )
                run_summary = gr.Markdown(
                    "_Click Query to load evidence artifacts._",
                    elem_classes=["af-summary", "af-empty-state"],
                )
                status_table = gr.Dataframe(
                    headers=[
                        "File", "Dataset", "Verdict", "Coherence", "Records", "Timestamp",
                    ],
                    column_count=6,
                    interactive=False, wrap=True,
                )

                def _query_with_summary(
                    ed: str, ds: str, v: str, df: str, dt: str,
                ) -> tuple[list[list[str]], str]:
                    rows = query_evidence(ed, ds, v, df, dt)
                    is_empty = len(rows) == 1 and "no artifacts" in rows[0][0].lower()
                    is_error = len(rows) == 1 and rows[0][0].startswith("(error")
                    if is_error:
                        summary = "Evidence query failed. Check the directory path."
                    elif is_empty:
                        summary = (
                            "No artifacts found matching the current filters. "
                            "Confirm the evidence directory path is correct."
                        )
                    else:
                        summary = _build_summary_line(rows)
                    return rows, summary

                query_btn.click(
                    fn=_query_with_summary,
                    inputs=[ev_dir, ds_filter, verdict_filter, from_filter, to_filter],
                    outputs=[status_table, run_summary],
                    queue=False,
                    show_progress="hidden",
                )

            # ---- Tab 3: Evidence Explorer ----
            with gr.Tab("Evidence Explorer", id="evidence_explorer"):
                gr.Markdown(
                    "Inspect the full JSON payload of a single evidence artifact. "
                    "Enter the filename from the Transformation Status table, "
                    "then click Load Artifact.",
                    elem_classes=["af-tab-desc"],
                )
                with gr.Row():
                    exp_dir = gr.Textbox(
                        label="Evidence Directory", value=EVIDENCE_DIR, scale=3,
                    )
                    exp_file = gr.Textbox(
                        label="Artifact Filename", value="",
                        placeholder="e.g. forge-evidence-20260403T140000_123456.json",
                        scale=3,
                    )
                    exp_btn = gr.Button("Load Artifact", variant="primary", scale=1)
                exp_meta = gr.Markdown(
                    "_Enter an artifact filename above and click Load Artifact._",
                    elem_classes=["af-summary", "af-empty-state"],
                )
                exp_json = gr.Code(
                    label="Artifact JSON", language="json", interactive=False,
                )

                def _load_with_meta(ed: str, fn: str) -> tuple[str, str]:
                    return load_artifact_detail(ed, fn), load_artifact_meta(ed, fn)

                exp_btn.click(
                    fn=_load_with_meta,
                    inputs=[exp_dir, exp_file],
                    outputs=[exp_json, exp_meta],
                    queue=False,
                    show_progress="hidden",
                )

                ev_dir.change(
                    fn=lambda d: d, inputs=[ev_dir], outputs=[exp_dir],
                    queue=False,
                    show_progress="hidden",
                )

                def _on_status_select(
                    current_dir: str, evt: gr.SelectData,
                ) -> tuple[str, str, str, str, Any]:
                    filename = ""
                    if isinstance(evt.row_value, list) and evt.row_value:
                        filename = str(evt.row_value[0])
                    detail, meta = _load_with_meta(current_dir, filename)
                    return (
                        current_dir, filename, detail, meta,
                        gr.Tabs(selected="evidence_explorer"),
                    )

                status_table.select(
                    fn=_on_status_select,
                    inputs=[ev_dir],
                    outputs=[exp_dir, exp_file, exp_json, exp_meta, tabs],
                    queue=False,
                    show_progress="hidden",
                )

            # ---- Tab 4: Analytics ----
            with gr.Tab("Analytics", id="analytics"):
                try:
                    from app.analytics import (
                        build_analytics_data,
                        build_coherence_histogram,
                        build_coherence_trend,
                        build_daily_volume,
                        build_verdict_bar,
                    )
                except (ImportError, ModuleNotFoundError):
                    from analytics import (  # type: ignore[no-redef]
                        build_analytics_data,
                        build_coherence_histogram,
                        build_coherence_trend,
                        build_daily_volume,
                        build_verdict_bar,
                    )

                gr.Markdown(
                    "Visual breakdown of transformation evidence. Click Refresh to "
                    "scan the evidence directory and update all charts.",
                    elem_classes=["af-tab-desc"],
                )
                with gr.Row():
                    ana_dir = gr.Textbox(
                        label="Evidence Directory", value=EVIDENCE_DIR, scale=3,
                    )
                    color_theme = gr.Dropdown(
                        choices=[
                            "Brand", "Traffic Light", "Colorblind Safe",
                            "Cyberpunk", "Pastel",
                        ],
                        value="Brand", label="Color Theme", scale=1,
                    )
                    ana_btn = gr.Button("Refresh", variant="primary", scale=1)
                ana_status = gr.Markdown(
                    "_Click Refresh to load analytics._",
                    elem_classes=["af-summary", "af-empty-state"],
                )

                with gr.Row():
                    verdict_plot = gr.Plot(label="Verdict Distribution")
                    coherence_hist_plot = gr.Plot(label="Coherence Score Distribution")
                with gr.Row():
                    volume_plot = gr.Plot(label="Daily Activity Volume")
                    trend_plot = gr.Plot(label="Coherence Trend")

                def _refresh_analytics(
                    edir: str, theme: str,
                ) -> tuple[Any, Any, Any, Any, str]:
                    records = build_analytics_data(edir.strip() or EVIDENCE_DIR)
                    if not records:
                        return None, None, None, None, "No evidence artifacts found."
                    verdict_fig = build_verdict_bar(records, theme)
                    hist_fig = build_coherence_histogram(records, theme)
                    vol_fig = build_daily_volume(records, theme)
                    trend_fig = build_coherence_trend(records, theme)
                    total = len(records)
                    return (
                        verdict_fig, hist_fig, vol_fig, trend_fig,
                        f"**{total} artifacts** analyzed",
                    )

            ana_btn.click(
                fn=_refresh_analytics,
                inputs=[ana_dir, color_theme],
                outputs=[verdict_plot, coherence_hist_plot, volume_plot, trend_plot, ana_status],
                queue=False,
                show_progress="hidden",
            )

        app.load(
            fn=_load_registry_with_status,
            inputs=[reg_path],
            outputs=[reg_table, reg_status],
            queue=False,
            show_progress="hidden",
        )

    return app


def _get_app():  # type: ignore[no-untyped-def]
    """Lazy app builder for module-level access."""
    return build_app()


# Databricks Apps runtime calls `gradio app.py` which expects a module-level `app`.
# Guarded so tests can import helpers without requiring gradio.
if gr is not None:
    app = _get_app()
    demo = app
else:
    app = None  # type: ignore[assignment]
    demo = None  # type: ignore[assignment]

if __name__ == "__main__":
    _app = _get_app()
    _app.launch()
