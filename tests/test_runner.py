"""Tests for the multi-dataset forge runner.

Traces: AF-IP-004 section 3, AF-SDD-001 section 4
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from aetheriaforge.config import ForgeContract
from aetheriaforge.config.registry import DatasetRegistry
from aetheriaforge.evidence import EvidenceWriter
from aetheriaforge.orchestration.runner import (
    DatasetInput,
    ForgeRunner,
)


def _contract_dict(
    name: str = "ds_a", version: str = "1.0.0"
) -> dict[str, object]:
    return {
        "dataset": {"name": name, "version": version},
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


def _diverse_df(n: int = 100) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": range(n),
            "category": [f"cat_{i % 10}" for i in range(n)],
            "value": [float(i) * 1.1 for i in range(n)],
        }
    )


def _registry_with(*names: str) -> DatasetRegistry:
    reg = DatasetRegistry()
    for name in names:
        reg.register(ForgeContract.from_dict(_contract_dict(name)))
    return reg


def _good_input() -> DatasetInput:
    df = _diverse_df()
    return DatasetInput(source_df=df, forged_df=df.copy())


# -- run_one ------------------------------------------------------------------


def test_run_one_pass() -> None:
    reg = _registry_with("ds_a")
    runner = ForgeRunner(reg)

    result = runner.run_one("ds_a", _good_input())

    assert result.pipeline_verdict == "PASS"
    assert result.dataset_name == "ds_a"


def test_run_one_unknown_dataset_raises() -> None:
    reg = _registry_with("ds_a")
    runner = ForgeRunner(reg)

    with pytest.raises(KeyError):
        runner.run_one("ds_unknown", _good_input())


# -- batch run ----------------------------------------------------------------


def test_batch_run_multiple_datasets() -> None:
    reg = _registry_with("ds_a", "ds_b")
    runner = ForgeRunner(reg)

    inputs = {
        "ds_a": _good_input(),
        "ds_b": _good_input(),
    }
    batch = runner.run(inputs)

    assert len(batch.results) == 2
    assert batch.batch_verdict == "PASS"
    assert "ds_a" in batch.results
    assert "ds_b" in batch.results


def test_batch_run_skips_unregistered() -> None:
    reg = _registry_with("ds_a")
    runner = ForgeRunner(reg)

    inputs = {
        "ds_a": _good_input(),
        "ds_orphan": _good_input(),
    }
    batch = runner.run(inputs)

    assert len(batch.results) == 1
    assert "ds_orphan" in batch.skipped


def test_batch_run_skips_unprovided() -> None:
    reg = _registry_with("ds_a", "ds_b")
    runner = ForgeRunner(reg)

    inputs = {"ds_a": _good_input()}
    batch = runner.run(inputs)

    assert len(batch.results) == 1
    assert "ds_b" in batch.skipped


# -- verdict aggregation ------------------------------------------------------


def test_batch_verdict_worst_of_datasets() -> None:
    reg = _registry_with("ds_good", "ds_bad")
    runner = ForgeRunner(reg)

    good_df = _diverse_df()
    bad_forged = good_df[["id"]].copy()
    bad_forged["id"] = 0

    inputs = {
        "ds_good": DatasetInput(source_df=good_df, forged_df=good_df.copy()),
        "ds_bad": DatasetInput(source_df=good_df, forged_df=bad_forged),
    }
    batch = runner.run(inputs)

    assert batch.batch_verdict == "FAIL"
    assert batch.results["ds_good"].pipeline_verdict == "PASS"
    assert batch.results["ds_bad"].pipeline_verdict == "FAIL"


def test_batch_empty_inputs() -> None:
    reg = _registry_with("ds_a")
    runner = ForgeRunner(reg)

    batch = runner.run({})

    assert len(batch.results) == 0
    assert batch.batch_verdict == "PASS"
    assert "ds_a" in batch.skipped


# -- evidence -----------------------------------------------------------------


def test_batch_run_writes_evidence(tmp_path: Path) -> None:
    reg = _registry_with("ds_a", "ds_b")
    writer = EvidenceWriter(tmp_path / "evidence")
    runner = ForgeRunner(reg, evidence_writer=writer)

    inputs = {
        "ds_a": _good_input(),
        "ds_b": _good_input(),
    }
    batch = runner.run(inputs)

    evidence_files = list((tmp_path / "evidence").glob("*.json"))
    assert len(evidence_files) == 2
    assert batch.results["ds_a"].evidence_path is not None
    assert batch.results["ds_b"].evidence_path is not None


# -- as_dict ------------------------------------------------------------------


def test_batch_result_as_dict() -> None:
    reg = _registry_with("ds_a")
    runner = ForgeRunner(reg)

    batch = runner.run({"ds_a": _good_input()})
    d = batch.as_dict()

    assert d["event"] == "batch_result"
    assert d["batch_verdict"] == "PASS"
    assert d["dataset_count"] == 1
    assert "ds_a" in d["datasets"]


# -- provenance ---------------------------------------------------------------


def test_run_one_execution_mode_threading() -> None:
    """execution_mode from DatasetInput is threaded into PipelineResult."""
    reg = _registry_with("ds_a")
    runner = ForgeRunner(reg)
    df = _diverse_df()
    inp = DatasetInput(source_df=df, forged_df=df.copy(), execution_mode="demo")

    result = runner.run_one("ds_a", inp)

    assert result.execution_mode == "demo"


def test_run_one_default_execution_mode_is_unverified() -> None:
    """DatasetInput default execution_mode is 'unverified'."""
    reg = _registry_with("ds_a")
    runner = ForgeRunner(reg)

    result = runner.run_one("ds_a", _good_input())

    assert result.execution_mode == "unverified"


def test_batch_evidence_contains_provenance(tmp_path: Path) -> None:
    """Batch evidence artifacts contain provenance fields."""
    reg = _registry_with("ds_a")
    writer = EvidenceWriter(tmp_path / "evidence")
    runner = ForgeRunner(reg, evidence_writer=writer)
    df = _diverse_df()
    inp = DatasetInput(
        source_df=df, forged_df=df.copy(), execution_mode="contract_backed",
    )

    batch = runner.run({"ds_a": inp})

    path = batch.results["ds_a"].evidence_path
    assert path is not None
    artifact = json.loads(Path(path).read_text())
    assert artifact["execution_mode"] == "contract_backed"
    assert artifact["source_location"] == "c.bronze.raw"
    assert artifact["contract_version"] == "1.0.0"
