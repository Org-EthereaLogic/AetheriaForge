"""Analytics chart builders for the AetheriaForge operator dashboard.

All functions are pure: they accept data and return Plotly figure objects.
No evidence files are read here — that is handled by the caller.
"""

from __future__ import annotations

import concurrent.futures
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import plotly.graph_objects as go

# -- Color palettes ----------------------------------------------------------

_PALETTES: dict[str, dict[str, str]] = {
    "Brand": {
        "PASS": "#22C7A0", "WARN": "#F59E0B", "FAIL": "#F97316",
        "bar": "#8B5CF6", "line": "#20CFE0",
    },
    "Traffic Light": {
        "PASS": "#22C55E", "WARN": "#EAB308", "FAIL": "#EF4444",
        "bar": "#3B82F6", "line": "#3B82F6",
    },
    "Colorblind Safe": {
        "PASS": "#009E73", "WARN": "#F0E442", "FAIL": "#D55E00",
        "bar": "#56B4E9", "line": "#56B4E9",
    },
    "Cyberpunk": {
        "PASS": "#00FF00", "WARN": "#FFE600", "FAIL": "#FF003C",
        "bar": "#00E5FF", "line": "#00E5FF",
    },
    "Pastel": {
        "PASS": "#86EFAC", "WARN": "#FDE047", "FAIL": "#FCA5A5",
        "bar": "#93C5FD", "line": "#93C5FD",
    },
}

_LAYOUT_DEFAULTS: dict[str, Any] = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {"color": "#CBD5E1"},
    "margin": {"l": 40, "r": 20, "t": 40, "b": 40},
}


def _get_palette(theme: str) -> dict[str, str]:
    return _PALETTES.get(theme, _PALETTES["Brand"])


# -- Data loading ------------------------------------------------------------

def _parse_analytics_artifact(fpath: Path) -> dict[str, Any] | None:
    try:
        return json.loads(fpath.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def build_analytics_data(evidence_dir: str) -> list[dict[str, Any]]:
    """Load all evidence JSON files and return parsed records."""
    path = Path(evidence_dir)
    if not path.is_dir():
        return []

    paths = [p for p in sorted(path.iterdir(), reverse=True) if p.suffix == ".json"]
    records: list[dict[str, Any]] = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        for result in executor.map(_parse_analytics_artifact, paths):
            if result is not None:
                records.append(result)

    return records


# -- Chart builders ----------------------------------------------------------

def build_verdict_bar(
    records: list[dict[str, Any]], theme: str = "Brand",
) -> go.Figure:
    """Bar chart of verdict distribution (PASS / WARN / FAIL)."""
    palette = _get_palette(theme)
    counts: Counter[str] = Counter()
    for r in records:
        v = str(r.get("pipeline_verdict", r.get("verdict", "UNKNOWN"))).upper()
        counts[v] += 1

    labels = ["PASS", "WARN", "FAIL"]
    values = [counts.get(label, 0) for label in labels]
    colors = [palette.get(label, "#64748B") for label in labels]

    fig = go.Figure(
        data=[go.Bar(x=labels, y=values, marker_color=colors)],
    )
    fig.update_layout(title="Verdict Distribution", yaxis_title="Count", **_LAYOUT_DEFAULTS)
    return fig


def build_coherence_histogram(
    records: list[dict[str, Any]], theme: str = "Brand",
) -> go.Figure:
    """Histogram of coherence scores across all artifacts."""
    palette = _get_palette(theme)
    scores: list[float] = []
    for r in records:
        forge = r.get("forge_result", {})
        score = forge.get("coherence_score")
        if isinstance(score, (int, float)):
            scores.append(float(score))

    fig = go.Figure(
        data=[go.Histogram(
            x=scores, nbinsx=20,
            marker_color=palette["bar"],
            marker_line_color="rgba(0,0,0,0.3)",
            marker_line_width=1,
        )],
    )
    fig.update_layout(
        title="Coherence Score Distribution",
        xaxis_title="Coherence Score",
        yaxis_title="Count",
        bargap=0.15,
        **_LAYOUT_DEFAULTS,
    )
    return fig


def build_daily_volume(
    records: list[dict[str, Any]], theme: str = "Brand",
) -> go.Figure:
    """Bar chart of artifacts per day."""
    palette = _get_palette(theme)
    day_counts: Counter[str] = Counter()
    for r in records:
        ts = r.get("run_at") or r.get("forged_at") or ""
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(str(ts))
            day_counts[dt.strftime("%Y-%m-%d")] += 1
        except ValueError:
            continue

    days = sorted(day_counts)
    values = [day_counts[d] for d in days]

    fig = go.Figure(
        data=[go.Bar(x=days, y=values, marker_color=palette["bar"])],
    )
    fig.update_layout(
        title="Daily Activity Volume",
        xaxis_title="Date",
        yaxis_title="Artifacts",
        **_LAYOUT_DEFAULTS,
    )
    return fig


def build_coherence_trend(
    records: list[dict[str, Any]], theme: str = "Brand",
) -> go.Figure:
    """Line chart of average coherence score per day."""
    palette = _get_palette(theme)
    day_scores: dict[str, list[float]] = {}
    for r in records:
        ts = r.get("run_at") or r.get("forged_at") or ""
        score = (r.get("forge_result") or {}).get("coherence_score")
        if not ts or not isinstance(score, (int, float)):
            continue
        try:
            dt = datetime.fromisoformat(str(ts))
            day = dt.strftime("%Y-%m-%d")
            day_scores.setdefault(day, []).append(float(score))
        except ValueError:
            continue

    days = sorted(day_scores)
    averages = [sum(day_scores[d]) / len(day_scores[d]) for d in days]

    fig = go.Figure(
        data=[go.Scatter(x=days, y=averages, mode="lines+markers", line={"color": palette["line"]})],
    )
    fig.update_layout(
        title="Coherence Trend",
        xaxis_title="Date",
        yaxis_title="Avg Coherence Score",
        **_LAYOUT_DEFAULTS,
    )
    return fig
