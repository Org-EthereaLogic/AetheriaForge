"""Tests for the orchestration pipeline.

Traces: AF-SDD-001 section 4, AF-SR-008, TP-001 sections 3+4
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from aetheriaforge.config import ForgeContract
from aetheriaforge.evidence import EvidenceWriter
from aetheriaforge.orchestration import ForgePipeline
from aetheriaforge.resolution import (
    MatchingConfig,
    ResolutionPolicy,
    SourceConfig,
)
from aetheriaforge.schema import ColumnSpec
from aetheriaforge.temporal import TemporalConfig


def _contract_data() -> dict[str, object]:
    """Return a minimal valid forge contract dictionary."""
    return {
        "dataset": {"name": "pipeline_ds", "version": "1.0.0"},
        "source": {"catalog": "c", "schema": "bronze", "table": "raw"},
        "target": {"catalog": "c", "schema": "silver", "table": "forged"},
        "coherence": {
            "engine": "shannon",
            "thresholds": {
                "bronze_min": 0.5,
                "silver_min": 0.75,
                "gold_min": 0.95,
            },
        },
        "schema_contract": {
            "enforce": True,
            "evolution": "versioned",
            "coerce_types": True,
        },
    }


@pytest.fixture()
def contract() -> ForgeContract:
    return ForgeContract.from_dict(_contract_data())


def _diverse_df(n: int = 100) -> pd.DataFrame:
    """Build a DataFrame with varied values to produce non-trivial entropy."""
    return pd.DataFrame(
        {
            "id": range(n),
            "category": [f"cat_{i % 10}" for i in range(n)],
            "value": [float(i) * 1.1 for i in range(n)],
        }
    )


# --- Pipeline verdict tests ---------------------------------------------------


def test_pipeline_pass_all_stages(contract: ForgeContract) -> None:
    """Full pipeline with good coherence produces PASS verdict."""
    pipeline = ForgePipeline(contract)
    source = _diverse_df()

    result = pipeline.run(source, source.copy())

    assert result.pipeline_verdict == "PASS"
    assert result.dataset_name == "pipeline_ds"
    assert result.forge_result is not None


def test_pipeline_forge_fail_propagates(contract: ForgeContract) -> None:
    """Forge FAIL from low coherence propagates to pipeline verdict."""
    pipeline = ForgePipeline(contract)
    source = _diverse_df()
    # Create a forged DF with collapsed entropy
    forged = source[["id"]].copy()
    forged["id"] = 0

    result = pipeline.run(source, forged)

    assert result.pipeline_verdict == "FAIL"


# --- Stage activation tests ---------------------------------------------------


def test_pipeline_with_schema_enforcement(contract: ForgeContract) -> None:
    """Pipeline with schema_columns sets enforcement_result."""
    pipeline = ForgePipeline(contract)
    source = _diverse_df()
    columns = [
        ColumnSpec(name="id", dtype="int64", nullable=False),
        ColumnSpec(name="category", dtype="object", nullable=True),
        ColumnSpec(name="value", dtype="float64", nullable=True),
    ]

    result = pipeline.run(source, source.copy(), schema_columns=columns)

    assert result.enforcement_result is not None
    assert len(result.enforcement_result.conformant) == len(source)


def test_pipeline_with_resolution(contract: ForgeContract) -> None:
    """Pipeline with resolution_policy and secondary_df sets resolution_result."""
    pipeline = ForgePipeline(contract)
    source = _diverse_df(10)
    forged = source.copy()

    secondary = pd.DataFrame({"id": range(10), "extra": range(10, 20)})
    policy = ResolutionPolicy(
        policy_name="test",
        version="1.0.0",
        sources=(
            SourceConfig(name="primary", key_columns=("id",), priority=1),
            SourceConfig(name="secondary", key_columns=("id",), priority=2),
        ),
        matching=MatchingConfig(
            strategy="exact",
            confidence_threshold=0.85,
            ambiguity_behavior="skip",
        ),
        record_all_decisions=True,
        include_rejected_matches=True,
    )

    result = pipeline.run(
        source, forged, secondary_df=secondary, resolution_policy=policy
    )

    assert result.resolution_result is not None
    assert result.resolution_result.resolved_count > 0


def test_pipeline_with_temporal(contract: ForgeContract) -> None:
    """Pipeline with temporal_config sets temporal_result."""
    pipeline = ForgePipeline(contract)
    source = pd.DataFrame(
        {
            "id": [1, 1, 2, 2],
            "category": ["a", "a", "b", "b"],
            "value": [1.0, 2.0, 3.0, 4.0],
            "event_ts": [
                "2024-01-01T10:00:00",
                "2024-01-01T11:00:00",
                "2024-01-01T10:00:00",
                "2024-01-01T12:00:00",
            ],
        }
    )
    forged = source.copy()
    temporal_config = TemporalConfig(
        timestamp_column="event_ts",
        merge_strategy="latest_wins",
        conflict_behavior="record_and_warn",
        entity_key_columns=("id",),
    )

    result = pipeline.run(source, forged, temporal_config=temporal_config)

    assert result.temporal_result is not None
    assert result.temporal_result.reconciled_count == 2


# --- Evidence tests -----------------------------------------------------------


def test_pipeline_evidence_written(
    contract: ForgeContract, tmp_path: Path
) -> None:
    """ForgePipeline with EvidenceWriter writes a pipeline evidence artifact."""
    writer = EvidenceWriter(tmp_path / "evidence")
    pipeline = ForgePipeline(contract, evidence_writer=writer)
    source = _diverse_df()

    result = pipeline.run(source, source.copy())

    assert result.evidence_path is not None
    assert Path(result.evidence_path).exists()


# --- as_dict tests ------------------------------------------------------------


def test_pipeline_result_as_dict(contract: ForgeContract) -> None:
    """as_dict() returns a dict with event=='pipeline_result'."""
    pipeline = ForgePipeline(contract)
    source = _diverse_df()

    result = pipeline.run(source, source.copy())
    d = result.as_dict()

    assert d["event"] == "pipeline_result"
    assert d["dataset_name"] == "pipeline_ds"
    assert "pipeline_verdict" in d
    assert "run_at" in d
    assert "forge_result" in d


# --- Verdict aggregation tests ------------------------------------------------


def test_pipeline_verdict_worst_of_stages(contract: ForgeContract) -> None:
    """Pipeline verdict is the worst of all stage verdicts."""
    pipeline = ForgePipeline(contract)
    source = _diverse_df()

    # Add a column that will have nulls to trigger quarantine (WARN)
    source_with_nulls = source.copy()
    source_with_nulls.loc[0, "id"] = None  # type: ignore[call-overload]
    columns = [
        ColumnSpec(name="id", dtype="int64", nullable=False),
        ColumnSpec(name="category", dtype="object", nullable=True),
        ColumnSpec(name="value", dtype="float64", nullable=True),
    ]

    result = pipeline.run(
        source_with_nulls,
        source.copy(),
        schema_columns=columns,
    )

    # Enforcement produces WARN from quarantine; forge may PASS or WARN.
    # The pipeline verdict should reflect the worst.
    assert result.pipeline_verdict in {"WARN", "FAIL"}
    assert result.enforcement_result is not None
    assert len(result.enforcement_result.quarantined) > 0
