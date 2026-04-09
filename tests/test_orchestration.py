"""Tests for the orchestration pipeline.

Traces: AF-SDD-001 section 4, AF-SR-008, TP-001 sections 3+4
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from aetheriaforge.config import ForgeContract
from aetheriaforge.evidence import EvidenceWriter
from aetheriaforge.orchestration import EXECUTION_MODES, ForgePipeline
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


def test_pipeline_transforms_from_inline_schema_contract() -> None:
    """Pipeline can derive a forged frame directly from contract schema metadata."""
    contract = ForgeContract.from_dict(
        {
            **_contract_data(),
            "schema_contract": {
                "enforce": True,
                "evolution": "versioned",
                "coerce_types": True,
                "contract": {
                    "name": "pipeline_schema",
                    "version": "2.0.0",
                    "layer": "silver",
                },
                "columns": [
                    {"name": "id", "type": "long", "nullable": False},
                    {
                        "name": "category",
                        "type": "string",
                        "nullable": True,
                        "transforms": [{"op": "upper"}],
                    },
                    {"name": "value", "type": "double", "nullable": True},
                ],
                "enforcement": {
                    "unknown_columns": "ignore",
                    "type_coercion": True,
                    "null_violation": "quarantine",
                },
            },
        }
    )
    pipeline = ForgePipeline(contract)
    source = _diverse_df(5)

    result = pipeline.run(source, include_forged_df=True)

    assert result.pipeline_verdict == "PASS"
    assert result.forged_df is not None
    assert list(result.forged_df.columns) == ["id", "category", "value"]
    assert result.forged_df.iloc[0]["category"].startswith("CAT_")
    assert result.schema_version == "2.0.0"


def test_pipeline_skips_enforcement_when_contract_disables_it() -> None:
    """schema_contract.enforce=false disables schema enforcement entirely."""
    contract = ForgeContract.from_dict(
        {
            **_contract_data(),
            "schema_contract": {
                "enforce": False,
                "evolution": "versioned",
                "coerce_types": True,
                "contract": {
                    "name": "pipeline_schema",
                    "version": "2.0.0",
                    "layer": "silver",
                },
                "columns": [{"name": "id", "type": "long", "nullable": False}],
            },
        }
    )
    pipeline = ForgePipeline(contract)

    result = pipeline.run(pd.DataFrame({"id": [1]}))

    assert result.enforcement_result is None


def test_pipeline_auto_loads_resolution_policy_from_contract() -> None:
    """resolution.enabled uses the inline contract policy when none is passed."""
    contract = ForgeContract.from_dict(
        {
            **_contract_data(),
            "resolution": {
                "enabled": True,
                "policy": {"name": "resolve", "version": "1.0.0"},
                "sources": [
                    {"name": "primary", "key_columns": ["id"], "priority": 1},
                    {"name": "secondary", "key_columns": ["id"], "priority": 2},
                ],
                "matching": {
                    "strategy": "exact",
                    "confidence_threshold": 0.85,
                    "ambiguity_behavior": "skip",
                },
                "evidence": {
                    "record_all_decisions": True,
                    "include_rejected_matches": True,
                },
            },
        }
    )
    pipeline = ForgePipeline(contract)
    source = _diverse_df(5)
    secondary = pd.DataFrame({"id": range(5), "extra": range(10, 15)})

    result = pipeline.run(source, source.copy(), secondary_df=secondary)

    assert result.resolution_result is not None
    assert result.resolution_result.resolved_count == 5


def test_pipeline_auto_loads_temporal_config_from_contract() -> None:
    """temporal.enabled uses the inline contract config when none is passed."""
    contract = ForgeContract.from_dict(
        {
            **_contract_data(),
            "temporal": {
                "enabled": True,
                "timestamp_column": "event_ts",
                "merge_strategy": "latest_wins",
                "conflict_behavior": "record_and_warn",
                "entity_key_columns": ["id"],
            },
        }
    )
    pipeline = ForgePipeline(contract)
    source = pd.DataFrame(
        {
            "id": [1, 1, 2],
            "category": ["a", "a", "b"],
            "value": [1.0, 2.0, 3.0],
            "event_ts": [
                "2024-01-01T10:00:00",
                "2024-01-01T11:00:00",
                "2024-01-01T09:00:00",
            ],
        }
    )

    result = pipeline.run(source, source.copy())

    assert result.temporal_result is not None
    assert result.temporal_result.reconciled_count == 2


def test_pipeline_enabled_resolution_requires_secondary_df() -> None:
    """A contract-enabled resolution stage fails closed without secondary data."""
    contract = ForgeContract.from_dict(
        {
            **_contract_data(),
            "resolution": {
                "enabled": True,
                "policy": {"name": "resolve", "version": "1.0.0"},
                "sources": [
                    {"name": "primary", "key_columns": ["id"], "priority": 1},
                    {"name": "secondary", "key_columns": ["id"], "priority": 2},
                ],
                "matching": {
                    "strategy": "exact",
                    "confidence_threshold": 0.85,
                    "ambiguity_behavior": "skip",
                },
                "evidence": {
                    "record_all_decisions": True,
                    "include_rejected_matches": True,
                },
            },
        }
    )
    pipeline = ForgePipeline(contract)

    with pytest.raises(ValueError, match="secondary dataset was provided"):
        pipeline.run(_diverse_df(5), _diverse_df(5))


def test_pipeline_missing_schema_contract_for_transform_raises(
    contract: ForgeContract,
) -> None:
    """Transformation requires either forged_df or a schema contract."""
    pipeline = ForgePipeline(contract)

    with pytest.raises(ValueError, match="No forged_df was supplied"):
        pipeline.run(_diverse_df(5))


def test_pipeline_resolution_enabled_requires_policy_definition() -> None:
    """Enabled resolution fails closed when no policy is configured."""
    contract = ForgeContract.from_dict(
        {
            **_contract_data(),
            "resolution": {"enabled": True},
        }
    )
    pipeline = ForgePipeline(contract)

    with pytest.raises(ValueError, match="resolution policy is configured"):
        pipeline.run(_diverse_df(5), _diverse_df(5), secondary_df=_diverse_df(5))


def test_pipeline_temporal_enabled_requires_complete_config() -> None:
    """Enabled temporal reconciliation fails closed when config is incomplete."""
    contract = ForgeContract.from_dict(
        {
            **_contract_data(),
            "temporal": {"enabled": True, "merge_strategy": "latest_wins"},
        }
    )
    pipeline = ForgePipeline(contract)

    with pytest.raises(ValueError, match="required temporal configuration is missing"):
        pipeline.run(_diverse_df(5), _diverse_df(5))


def test_pipeline_schema_contract_defaults_to_forge_contract_enforcement() -> None:
    """Forge-contract enforcement remains the fallback when schema contract omits it."""
    contract = ForgeContract.from_dict(
        {
            **_contract_data(),
            "schema_contract": {
                "enforce": True,
                "evolution": "versioned",
                "coerce_types": True,
                "unknown_columns": "reject",
                "null_violation": "reject",
                "contract": {
                    "name": "pipeline_schema",
                    "version": "2.0.0",
                    "layer": "silver",
                },
                "columns": [{"name": "id", "type": "long", "nullable": False}],
            },
        }
    )
    pipeline = ForgePipeline(contract)
    forged = pd.DataFrame({"id": [1], "extra": ["x"]})

    result = pipeline.run(
        pd.DataFrame({"id": [1]}),
        forged,
        include_forged_df=True,
    )

    assert result.enforcement_result is not None
    assert len(result.enforcement_result.quarantined) == 1
    assert result.enforcement_result.conformant.empty


def test_pipeline_include_forged_df_controls_result_retention() -> None:
    """The caller can opt into retaining the forged DataFrame on the result."""
    contract = ForgeContract.from_dict(
        {
            **_contract_data(),
            "schema_contract": {
                "enforce": False,
                "evolution": "versioned",
                "coerce_types": True,
                "contract": {
                    "name": "pipeline_schema",
                    "version": "2.0.0",
                    "layer": "silver",
                },
                "columns": [{"name": "id", "type": "long", "nullable": False}],
            },
        }
    )
    pipeline = ForgePipeline(contract)
    source = pd.DataFrame({"id": [1]})

    default_result = pipeline.run(source)
    kept_result = pipeline.run(source, include_forged_df=True)

    assert default_result.forged_df is None
    assert kept_result.forged_df is not None


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
    """as_dict() returns a dict with event=='pipeline_result' and provenance."""
    pipeline = ForgePipeline(contract)
    source = _diverse_df()

    result = pipeline.run(source, source.copy())
    d = result.as_dict()

    assert d["event"] == "pipeline_result"
    assert d["dataset_name"] == "pipeline_ds"
    assert "pipeline_verdict" in d
    assert "run_at" in d
    assert "forge_result" in d
    # Provenance fields must always be present.
    assert d["execution_mode"] == "unverified"
    assert d["source_location"] == "c.bronze.raw"
    assert d["target_location"] == "c.silver.forged"
    assert d["contract_version"] == "1.0.0"


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
        source_with_nulls.copy(),
        schema_columns=columns,
    )

    # Enforcement produces WARN from quarantine; forge may PASS or WARN.
    # The pipeline verdict should reflect the worst.
    assert result.pipeline_verdict in {"WARN", "FAIL"}
    assert result.enforcement_result is not None
    assert len(result.enforcement_result.quarantined) > 0


# --- Provenance tests ---------------------------------------------------------


def test_pipeline_execution_mode_threading(contract: ForgeContract) -> None:
    """execution_mode is threaded into the PipelineResult."""
    pipeline = ForgePipeline(contract)
    source = _diverse_df()

    result = pipeline.run(source, source.copy(), execution_mode="demo")

    assert result.execution_mode == "demo"
    assert result.as_dict()["execution_mode"] == "demo"


def test_pipeline_contract_backed_mode(contract: ForgeContract) -> None:
    """contract_backed execution_mode is accepted and recorded."""
    pipeline = ForgePipeline(contract)
    source = _diverse_df()

    result = pipeline.run(source, source.copy(), execution_mode="contract_backed")

    assert result.execution_mode == "contract_backed"


def test_pipeline_invalid_execution_mode_raises(contract: ForgeContract) -> None:
    """Invalid execution_mode raises ValueError."""
    pipeline = ForgePipeline(contract)
    source = _diverse_df()

    with pytest.raises(ValueError, match="Invalid execution_mode"):
        pipeline.run(source, source.copy(), execution_mode="production")


def test_pipeline_default_execution_mode_is_unverified(contract: ForgeContract) -> None:
    """Default execution_mode is 'unverified' — never silently claims contract-backed."""
    pipeline = ForgePipeline(contract)
    source = _diverse_df()

    result = pipeline.run(source, source.copy())

    assert result.execution_mode == "unverified"


def test_pipeline_provenance_fields_in_result(contract: ForgeContract) -> None:
    """Provenance fields from the contract appear in the PipelineResult."""
    pipeline = ForgePipeline(contract)
    source = _diverse_df()

    result = pipeline.run(source, source.copy())

    assert result.source_location == "c.bronze.raw"
    assert result.target_location == "c.silver.forged"
    assert result.contract_version == "1.0.0"


def test_pipeline_evidence_artifact_contains_provenance(
    contract: ForgeContract, tmp_path: Path
) -> None:
    """Written evidence artifact JSON contains all provenance fields."""
    writer = EvidenceWriter(tmp_path / "evidence")
    pipeline = ForgePipeline(contract, evidence_writer=writer)
    source = _diverse_df()

    result = pipeline.run(source, source.copy(), execution_mode="demo")

    assert result.evidence_path is not None
    artifact = json.loads(Path(result.evidence_path).read_text())
    assert artifact["execution_mode"] == "demo"
    assert artifact["source_location"] == "c.bronze.raw"
    assert artifact["target_location"] == "c.silver.forged"
    assert artifact["contract_version"] == "1.0.0"
    assert artifact["dataset_name"] == "pipeline_ds"


def test_execution_modes_constant() -> None:
    """EXECUTION_MODES is a frozen set of known valid modes."""
    assert "demo" in EXECUTION_MODES
    assert "contract_backed" in EXECUTION_MODES
    assert "unverified" in EXECUTION_MODES
    assert "notebook" in EXECUTION_MODES
