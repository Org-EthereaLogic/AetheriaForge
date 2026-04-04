"""Tests for the forge engine — coherence scoring, verdicts, and evidence.

Traces: AF-SR-002, AF-FR-005, AF-FR-006, AF-FR-012
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from aetheriaforge.config import ForgeContract
from aetheriaforge.evidence import EvidenceWriter
from aetheriaforge.forge import ForgeEngine, shannon_coherence_score


def _contract_data(
    silver_min: float = 0.75,
    bronze_min: float = 0.5,
    gold_min: float = 0.95,
) -> dict[str, object]:
    return {
        "dataset": {"name": "test_ds", "version": "1.0.0"},
        "source": {"catalog": "c", "schema": "bronze", "table": "raw"},
        "target": {"catalog": "c", "schema": "silver", "table": "forged"},
        "coherence": {
            "engine": "shannon",
            "thresholds": {
                "bronze_min": bronze_min,
                "silver_min": silver_min,
                "gold_min": gold_min,
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


# --- Coherence score tests ---------------------------------------------------


def test_perfect_coherence_score() -> None:
    """Identical source and forged frames produce a score of 1.0."""
    df = _diverse_df()
    assert shannon_coherence_score(df, df.copy()) == 1.0


def test_column_drop_reduces_score() -> None:
    """Dropping a source column from forged lowers the coherence score."""
    source = _diverse_df()
    forged = source.drop(columns=["category"])
    score = shannon_coherence_score(source, forged)

    assert score < 1.0
    assert score > 0.0


def test_coherence_score_determinism() -> None:
    """The same inputs always produce the same score."""
    source = _diverse_df()
    forged = source.drop(columns=["value"])
    scores = [shannon_coherence_score(source, forged) for _ in range(3)]

    assert scores[0] == scores[1] == scores[2]


# --- Forge engine verdict tests -----------------------------------------------


def test_forge_pass_verdict(contract: ForgeContract) -> None:
    """Score above the silver threshold produces PASS with no failure reason."""
    source = _diverse_df()
    engine = ForgeEngine(contract)
    result = engine.forge(source, source.copy(), target_layer="silver")

    assert result.verdict == "PASS"
    assert result.failure_reason is None


def test_forge_fail_verdict(contract: ForgeContract) -> None:
    """Heavily reduced forged frame produces FAIL with a failure reason."""
    source = _diverse_df()
    forged = source[["id"]].copy()
    forged["id"] = 0  # constant column — entropy collapses
    engine = ForgeEngine(contract)
    result = engine.forge(source, forged, target_layer="silver")

    assert result.verdict == "FAIL"
    assert result.failure_reason is not None


def test_forge_warn_verdict() -> None:
    """Score in the WARN zone produces verdict WARN."""
    # silver_min=0.8, WARN_TOLERANCE=0.05 → WARN zone is [0.75, 0.80).
    # Construct a source where dropping a low-entropy column gives score ~0.769.
    data = _contract_data(silver_min=0.8)
    warn_contract = ForgeContract.from_dict(data)

    source = pd.DataFrame(
        {
            "main": range(100),
            "minor": [i % 4 for i in range(100)],
        }
    )
    forged = source[["main"]].copy()

    # Verify the fixture lands in the WARN zone.
    score = shannon_coherence_score(source, forged)
    assert 0.75 <= score < 0.80, f"Fixture score {score} outside WARN zone"

    engine = ForgeEngine(warn_contract)
    result = engine.forge(source, forged, target_layer="silver")

    assert result.verdict == "WARN"
    assert result.failure_reason is not None


# --- Evidence integration tests -----------------------------------------------


def test_forge_writes_evidence(contract: ForgeContract, tmp_path: Path) -> None:
    """ForgeEngine with an EvidenceWriter creates a valid evidence artifact."""
    writer = EvidenceWriter(tmp_path / "evidence")
    engine = ForgeEngine(contract, evidence_writer=writer)
    source = _diverse_df()
    result = engine.forge(source, source.copy())

    assert result.evidence_path is not None
    assert Path(result.evidence_path).exists()
    # Verify content is valid and contains expected fields.
    artifact = json.loads(Path(result.evidence_path).read_text())
    assert artifact["event"] == "forge_result"
    assert artifact["dataset_name"] == "test_ds"
    assert isinstance(artifact["coherence_score"], float)
    assert artifact["verdict"] in {"PASS", "WARN", "FAIL"}


def test_forge_no_evidence_writer(contract: ForgeContract) -> None:
    """ForgeEngine without an evidence_writer leaves evidence_path as None."""
    engine = ForgeEngine(contract)
    source = _diverse_df()
    result = engine.forge(source, source.copy())

    assert result.evidence_path is None


# --- ForgeResult field tests --------------------------------------------------


def test_forge_result_fields(contract: ForgeContract) -> None:
    """All ForgeResult fields are populated after a forge operation."""
    engine = ForgeEngine(contract)
    source = _diverse_df()
    result = engine.forge(source, source.copy())

    assert result.dataset_name == "test_ds"
    assert 0.0 <= result.coherence_score <= 1.0
    assert result.verdict in {"PASS", "WARN", "FAIL"}
    assert result.threshold == 0.75
    assert result.records_in == len(source)
    assert result.records_out == len(source)
    assert result.forged_at  # non-empty ISO 8601 string
    assert result.columns_in == list(source.columns)
    assert result.columns_out == list(source.columns)


def test_forge_result_as_dict(contract: ForgeContract) -> None:
    """as_dict() returns a dict with event=='forge_result' and all fields."""
    engine = ForgeEngine(contract)
    source = _diverse_df()
    result = engine.forge(source, source.copy())
    d = result.as_dict()

    assert d["event"] == "forge_result"
    assert d["dataset_name"] == "test_ds"
    assert "coherence_score" in d
    assert "verdict" in d
    assert "threshold" in d
    assert "records_in" in d
    assert "records_out" in d
    assert "forged_at" in d
    assert "columns_in" in d
    assert "columns_out" in d
