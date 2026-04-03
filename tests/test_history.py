"""Tests for transformation history query interface.

Traces: AF-IP-004 section 2, AF-SDD-001 section 3
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from aetheriaforge.evidence.history import TransformationHistory


def _write_evidence(
    evidence_dir: Path,
    dataset_name: str = "ds_a",
    verdict: str = "PASS",
    run_at: str = "2026-04-01T10:00:00+00:00",
    suffix: str = "000001",
) -> Path:
    """Write a synthetic evidence artifact and return its path."""
    evidence_dir.mkdir(parents=True, exist_ok=True)
    artifact = {
        "event": "pipeline_result",
        "dataset_name": dataset_name,
        "pipeline_verdict": verdict,
        "run_at": run_at,
    }
    ts = run_at.replace(":", "").replace("-", "").replace("+", "")[:15]
    path = evidence_dir / f"forge-evidence-{ts}_{suffix}.json"
    path.write_text(json.dumps(artifact))
    return path


# -- list_all -----------------------------------------------------------------


def test_list_all_returns_artifacts(tmp_path: Path) -> None:
    ev_dir = tmp_path / "evidence"
    _write_evidence(ev_dir, suffix="000001")
    _write_evidence(ev_dir, suffix="000002")

    history = TransformationHistory(ev_dir)
    assert len(history.list_all()) == 2


def test_list_all_empty_dir(tmp_path: Path) -> None:
    history = TransformationHistory(tmp_path / "nonexistent")
    assert history.list_all() == []


# -- query by dataset ---------------------------------------------------------


def test_query_by_dataset_name(tmp_path: Path) -> None:
    ev_dir = tmp_path / "evidence"
    _write_evidence(ev_dir, dataset_name="ds_a", suffix="000001")
    _write_evidence(ev_dir, dataset_name="ds_b", suffix="000002")

    history = TransformationHistory(ev_dir)
    results = history.query(dataset_name="ds_a")
    assert len(results) == 1
    assert results[0]["dataset_name"] == "ds_a"


# -- query by verdict ---------------------------------------------------------


def test_query_by_verdict(tmp_path: Path) -> None:
    ev_dir = tmp_path / "evidence"
    _write_evidence(ev_dir, verdict="PASS", suffix="000001")
    _write_evidence(ev_dir, verdict="FAIL", suffix="000002")
    _write_evidence(ev_dir, verdict="PASS", suffix="000003")

    history = TransformationHistory(ev_dir)
    results = history.query(verdict="FAIL")
    assert len(results) == 1
    assert results[0]["pipeline_verdict"] == "FAIL"


# -- query by time range ------------------------------------------------------


def test_query_by_time_range(tmp_path: Path) -> None:
    ev_dir = tmp_path / "evidence"
    _write_evidence(ev_dir, run_at="2026-04-01T08:00:00+00:00", suffix="000001")
    _write_evidence(ev_dir, run_at="2026-04-01T12:00:00+00:00", suffix="000002")
    _write_evidence(ev_dir, run_at="2026-04-02T08:00:00+00:00", suffix="000003")

    history = TransformationHistory(ev_dir)
    after_dt = datetime(2026, 4, 1, 10, 0, 0, tzinfo=timezone.utc)
    before_dt = datetime(2026, 4, 1, 23, 59, 59, tzinfo=timezone.utc)

    results = history.query(after=after_dt, before=before_dt)
    assert len(results) == 1
    assert "12:00:00" in results[0]["run_at"]


# -- combined filters ---------------------------------------------------------


def test_query_combined_filters(tmp_path: Path) -> None:
    ev_dir = tmp_path / "evidence"
    _write_evidence(ev_dir, dataset_name="ds_a", verdict="PASS", suffix="000001")
    _write_evidence(ev_dir, dataset_name="ds_a", verdict="FAIL", suffix="000002")
    _write_evidence(ev_dir, dataset_name="ds_b", verdict="PASS", suffix="000003")

    history = TransformationHistory(ev_dir)
    results = history.query(dataset_name="ds_a", verdict="PASS")
    assert len(results) == 1


# -- summary ------------------------------------------------------------------


def test_summary_groups_by_dataset_and_verdict(tmp_path: Path) -> None:
    ev_dir = tmp_path / "evidence"
    _write_evidence(ev_dir, dataset_name="ds_a", verdict="PASS", suffix="000001")
    _write_evidence(ev_dir, dataset_name="ds_a", verdict="PASS", suffix="000002")
    _write_evidence(ev_dir, dataset_name="ds_a", verdict="FAIL", suffix="000003")
    _write_evidence(ev_dir, dataset_name="ds_b", verdict="PASS", suffix="000004")

    history = TransformationHistory(ev_dir)
    s = history.summary()
    assert s["ds_a"]["PASS"] == 2
    assert s["ds_a"]["FAIL"] == 1
    assert s["ds_b"]["PASS"] == 1


# -- malformed tolerance ------------------------------------------------------


def test_malformed_file_skipped(tmp_path: Path) -> None:
    ev_dir = tmp_path / "evidence"
    ev_dir.mkdir(parents=True)

    _write_evidence(ev_dir, suffix="000001")
    (ev_dir / "forge-evidence-bad.json").write_text("NOT VALID JSON{{{")

    history = TransformationHistory(ev_dir)
    results = history.list_all()
    assert len(results) == 1
