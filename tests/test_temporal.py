"""Tests for temporal reconciliation engine.

Traces: AF-SR-004, AF-FR-008, TP-001 section 4
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from aetheriaforge.evidence import EvidenceWriter
from aetheriaforge.temporal import TemporalConfig, TemporalReconciler


def _make_config(
    conflict_behavior: str = "record_and_warn",
    merge_strategy: str = "latest_wins",
    entity_key_columns: tuple[str, ...] = ("entity_id",),
) -> TemporalConfig:
    """Build a minimal TemporalConfig for testing."""
    return TemporalConfig(
        timestamp_column="event_ts",
        merge_strategy=merge_strategy,
        conflict_behavior=conflict_behavior,
        entity_key_columns=entity_key_columns,
    )


# --- latest_wins tests --------------------------------------------------------


def test_latest_wins_single_record() -> None:
    """A single record per entity passes through unchanged."""
    config = _make_config()
    reconciler = TemporalReconciler(config)

    df = pd.DataFrame(
        {"entity_id": [1], "event_ts": ["2024-01-01T10:00:00"], "value": [42]}
    )

    result = reconciler.reconcile(df)

    assert len(result.reconciled) == 1
    assert result.reconciled_count == 1
    assert result.conflict_count == 0


def test_latest_wins_takes_latest() -> None:
    """Two records for one entity: reconciled keeps the latest timestamp."""
    config = _make_config()
    reconciler = TemporalReconciler(config)

    df = pd.DataFrame(
        {
            "entity_id": [1, 1],
            "event_ts": ["2024-01-01T10:00:00", "2024-01-01T11:00:00"],
            "value": [10, 20],
        }
    )

    result = reconciler.reconcile(df)

    assert len(result.reconciled) == 1
    assert result.reconciled.iloc[0]["event_ts"] == "2024-01-01T11:00:00"
    assert result.reconciled.iloc[0]["value"] == 20
    assert result.conflict_count == 0


def test_latest_wins_determinism() -> None:
    """The same input produces identical reconciled output across runs."""
    config = _make_config()

    df = pd.DataFrame(
        {
            "entity_id": [1, 1, 2],
            "event_ts": [
                "2024-01-01T10:00:00",
                "2024-01-01T11:00:00",
                "2024-01-01T09:00:00",
            ],
            "value": [10, 20, 30],
        }
    )

    results = [TemporalReconciler(config).reconcile(df) for _ in range(3)]

    for r in results[1:]:
        pd.testing.assert_frame_equal(results[0].reconciled, r.reconciled)


def test_duplicate_timestamp_conflict_recorded() -> None:
    """Duplicate timestamps with record_and_warn records a conflict but reconciles."""
    config = _make_config(conflict_behavior="record_and_warn")
    reconciler = TemporalReconciler(config)

    df = pd.DataFrame(
        {
            "entity_id": [1, 1],
            "event_ts": ["2024-01-01T10:00:00", "2024-01-01T10:00:00"],
            "value": [10, 20],
        }
    )

    result = reconciler.reconcile(df)

    assert len(result.reconciled) == 1
    assert result.conflict_count == 1
    assert result.conflicts[0].conflict_type == "DUPLICATE_TIMESTAMP"


def test_duplicate_timestamp_conflict_fail() -> None:
    """Duplicate timestamps with conflict_behavior='fail' raises ValueError."""
    config = _make_config(conflict_behavior="fail")
    reconciler = TemporalReconciler(config)

    df = pd.DataFrame(
        {
            "entity_id": [1, 1],
            "event_ts": ["2024-01-01T10:00:00", "2024-01-01T10:00:00"],
            "value": [10, 20],
        }
    )

    with pytest.raises(ValueError, match="Duplicate timestamp conflict"):
        reconciler.reconcile(df)


def test_multiple_entities_reconciled() -> None:
    """Three entities with two records each reconcile to three rows."""
    config = _make_config()
    reconciler = TemporalReconciler(config)

    df = pd.DataFrame(
        {
            "entity_id": [1, 1, 2, 2, 3, 3],
            "event_ts": [
                "2024-01-01T10:00:00",
                "2024-01-01T11:00:00",
                "2024-01-01T10:00:00",
                "2024-01-01T12:00:00",
                "2024-01-01T10:00:00",
                "2024-01-01T13:00:00",
            ],
            "value": [10, 20, 30, 40, 50, 60],
        }
    )

    result = reconciler.reconcile(df)

    assert len(result.reconciled) == 3
    assert result.reconciled_count == 3
    assert result.conflict_count == 0


def test_missing_timestamp_column_raises() -> None:
    """Missing timestamp column raises ValueError."""
    config = _make_config()
    reconciler = TemporalReconciler(config)

    df = pd.DataFrame({"entity_id": [1], "wrong_ts": ["2024-01-01T10:00:00"]})

    with pytest.raises(ValueError, match="Missing required columns"):
        reconciler.reconcile(df)


# --- Evidence tests -----------------------------------------------------------


def test_temporal_evidence_written(tmp_path: Path) -> None:
    """TemporalReconciler with EvidenceWriter writes an evidence artifact."""
    config = _make_config()
    writer = EvidenceWriter(tmp_path / "evidence")
    reconciler = TemporalReconciler(config, evidence_writer=writer)

    df = pd.DataFrame(
        {"entity_id": [1], "event_ts": ["2024-01-01T10:00:00"], "value": [42]}
    )

    result = reconciler.reconcile(df)

    assert result.evidence_path is not None
    assert Path(result.evidence_path).exists()


def test_temporal_result_as_dict() -> None:
    """as_dict() returns a dict with event=='temporal_result'."""
    config = _make_config()
    reconciler = TemporalReconciler(config)

    df = pd.DataFrame(
        {"entity_id": [1], "event_ts": ["2024-01-01T10:00:00"], "value": [42]}
    )

    result = reconciler.reconcile(df)
    d = result.as_dict()

    assert d["event"] == "temporal_result"
    assert "conflict_count" in d
    assert "reconciled_count" in d
    assert "reconciled_at" in d
    assert "conflicts" in d
    assert "merge_decisions" in d
