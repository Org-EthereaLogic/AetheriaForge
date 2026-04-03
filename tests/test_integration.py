"""Tests for the DriftSentinel integration layer.

Traces: AF-TP-001 section 6, AF-SR-012, AF-SR-013, AF-FR-013, AF-FR-014,
        AF-NFR-011, AF-SNFR-011
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from aetheriaforge.config import ForgeContract
from aetheriaforge.config.registry import DatasetRegistry
from aetheriaforge.evidence import EvidenceWriter
from aetheriaforge.integration.config import BundledModeConfig, discover_bundled_config
from aetheriaforge.integration.drift import (
    ColumnDriftReport,
    DriftIngester,
    DriftReport,
    RemediationAction,
)
from aetheriaforge.integration.events import (
    EventChannel,
    FileEventChannel,
    NullEventChannel,
    TransformationEvent,
)
from aetheriaforge.orchestration import ForgePipeline
from aetheriaforge.orchestration.runner import DatasetInput, ForgeRunner

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _contract_data() -> dict[str, object]:
    """Return a minimal valid forge contract dictionary."""
    return {
        "dataset": {"name": "integ_ds", "version": "1.0.0"},
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
    return pd.DataFrame(
        {
            "id": range(n),
            "category": [f"cat_{i % 10}" for i in range(n)],
            "value": [float(i) * 1.1 for i in range(n)],
        }
    )


# ===========================================================================
# BundledModeConfig tests (WBS 3.3)
# ===========================================================================


class TestBundledModeConfig:
    """Tests for bundled-mode configuration loading."""

    def test_from_dict_enabled(self) -> None:
        """Correctly parses an enabled config."""
        data = {
            "enabled": True,
            "events_dir": "/dbfs/events/af",
            "drift_dir": "/dbfs/events/ds",
            "auto_ingest": True,
        }
        cfg = BundledModeConfig.from_dict(data)

        assert cfg.enabled is True
        assert cfg.events_dir == "/dbfs/events/af"
        assert cfg.drift_dir == "/dbfs/events/ds"
        assert cfg.auto_ingest is True

    def test_from_dict_disabled(self) -> None:
        """Missing or false enabled produces disabled config."""
        cfg = BundledModeConfig.from_dict({})

        assert cfg.enabled is False
        assert cfg.events_dir == ""

    def test_disabled_factory(self) -> None:
        """`disabled()` returns `enabled=False`."""
        cfg = BundledModeConfig.disabled()

        assert cfg.enabled is False
        assert cfg.auto_ingest is False

    def test_frozen(self) -> None:
        """BundledModeConfig is immutable."""
        cfg = BundledModeConfig.disabled()
        with pytest.raises(AttributeError):
            cfg.enabled = True  # type: ignore[misc]

    def test_from_yaml(self, tmp_path: Path) -> None:
        """Load from a YAML file."""
        config_file = tmp_path / "bundled.yml"
        config_file.write_text(
            "integration:\n  enabled: true\n  events_dir: /tmp/events\n"
        )
        cfg = BundledModeConfig.from_yaml(config_file)

        assert cfg.enabled is True
        assert cfg.events_dir == "/tmp/events"

    def test_discover_no_sources(self) -> None:
        """discover_bundled_config() with no arguments returns disabled."""
        cfg = discover_bundled_config()

        assert cfg.enabled is False

    def test_discover_from_contract_raw(self) -> None:
        """Extracts integration section from a contract dict."""
        raw = {"integration": {"enabled": True, "events_dir": "/events"}}
        cfg = discover_bundled_config(contract_raw=raw)

        assert cfg.enabled is True
        assert cfg.events_dir == "/events"

    def test_discover_config_path_priority(self, tmp_path: Path) -> None:
        """Config path takes priority over contract_raw."""
        config_file = tmp_path / "bundled.yml"
        config_file.write_text(
            "integration:\n  enabled: true\n  events_dir: /from-file\n"
        )
        raw = {"integration": {"enabled": True, "events_dir": "/from-contract"}}
        cfg = discover_bundled_config(contract_raw=raw, config_path=config_file)

        assert cfg.events_dir == "/from-file"


# ===========================================================================
# TransformationEvent tests (WBS 3.1)
# ===========================================================================


class TestTransformationEvent:
    """Tests for transformation event data shapes."""

    def test_from_pipeline_result(self, contract: ForgeContract) -> None:
        """Factory correctly extracts fields from a PipelineResult."""
        pipeline = ForgePipeline(contract)
        source = _diverse_df()
        result = pipeline.run(source, source.copy())

        event = TransformationEvent.from_pipeline_result(result, contract)

        assert event.event_type == "pipeline_result"
        assert event.dataset_name == "integ_ds"
        assert event.dataset_version == "1.0.0"
        assert event.coherence_score is not None
        assert event.verdict == result.pipeline_verdict
        assert event.run_at == result.run_at
        assert isinstance(event.payload, dict)

    def test_frozen(self, contract: ForgeContract) -> None:
        """TransformationEvent is immutable."""
        pipeline = ForgePipeline(contract)
        source = _diverse_df()
        result = pipeline.run(source, source.copy())
        event = TransformationEvent.from_pipeline_result(result, contract)

        with pytest.raises(AttributeError):
            event.verdict = "FAIL"  # type: ignore[misc]

    def test_resolution_outcome_none_when_no_resolution(
        self, contract: ForgeContract
    ) -> None:
        """resolution_outcome is None when resolution was not run."""
        pipeline = ForgePipeline(contract)
        source = _diverse_df()
        result = pipeline.run(source, source.copy())
        event = TransformationEvent.from_pipeline_result(result, contract)

        assert event.resolution_outcome is None

    def test_payload_contains_required_fields(
        self, contract: ForgeContract
    ) -> None:
        """The payload dict contains the expected keys."""
        pipeline = ForgePipeline(contract)
        source = _diverse_df()
        result = pipeline.run(source, source.copy())
        event = TransformationEvent.from_pipeline_result(result, contract)

        assert "event" in event.payload
        assert "dataset_name" in event.payload
        assert "forge_result" in event.payload


# ===========================================================================
# EventChannel tests (WBS 3.1)
# ===========================================================================


class TestNullEventChannel:
    """Tests for the no-op channel."""

    def test_no_op_completes(self, contract: ForgeContract) -> None:
        """NullEventChannel.emit() completes without error."""
        channel = NullEventChannel()
        pipeline = ForgePipeline(contract)
        source = _diverse_df()
        result = pipeline.run(source, source.copy())
        event = TransformationEvent.from_pipeline_result(result, contract)

        channel.emit(event)  # should not raise

    def test_satisfies_protocol(self) -> None:
        """NullEventChannel satisfies the EventChannel protocol."""
        channel = NullEventChannel()
        assert isinstance(channel, EventChannel)


class TestFileEventChannel:
    """Tests for the file-based event channel."""

    def test_writes_json(
        self, contract: ForgeContract, tmp_path: Path
    ) -> None:
        """FileEventChannel.emit() writes a JSON file."""
        events_dir = tmp_path / "events"
        channel = FileEventChannel(events_dir)
        pipeline = ForgePipeline(contract)
        source = _diverse_df()
        result = pipeline.run(source, source.copy())
        event = TransformationEvent.from_pipeline_result(result, contract)

        channel.emit(event)

        files = list(events_dir.glob("af-event-*.json"))
        assert len(files) == 1
        payload = json.loads(files[0].read_text())
        assert payload["event_type"] == "pipeline_result"
        assert payload["dataset_name"] == "integ_ds"

    def test_satisfies_protocol(self, tmp_path: Path) -> None:
        """FileEventChannel satisfies the EventChannel protocol."""
        channel = FileEventChannel(tmp_path / "events")
        assert isinstance(channel, EventChannel)

    def test_creates_directory(self, contract: ForgeContract, tmp_path: Path) -> None:
        """FileEventChannel creates the events directory if it doesn't exist."""
        events_dir = tmp_path / "nested" / "events"
        channel = FileEventChannel(events_dir)
        pipeline = ForgePipeline(contract)
        source = _diverse_df()
        result = pipeline.run(source, source.copy())
        event = TransformationEvent.from_pipeline_result(result, contract)

        channel.emit(event)

        assert events_dir.exists()


# ===========================================================================
# Pipeline event emission tests (WBS 3.1 — wire-up)
# ===========================================================================


class TestPipelineEventEmission:
    """Tests for event emission wired into ForgePipeline."""

    def test_pipeline_emits_event_when_channel_provided(
        self, contract: ForgeContract, tmp_path: Path
    ) -> None:
        """ForgePipeline.run() emits an event when event_channel is set."""
        events_dir = tmp_path / "events"
        channel = FileEventChannel(events_dir)
        pipeline = ForgePipeline(contract, event_channel=channel)
        source = _diverse_df()

        pipeline.run(source, source.copy())

        files = list(events_dir.glob("af-event-*.json"))
        assert len(files) == 1

    def test_pipeline_no_event_when_channel_none(
        self, contract: ForgeContract, tmp_path: Path
    ) -> None:
        """ForgePipeline.run() writes no event files in standalone mode."""
        events_dir = tmp_path / "events"
        events_dir.mkdir()
        pipeline = ForgePipeline(contract)
        source = _diverse_df()

        pipeline.run(source, source.copy())

        files = list(events_dir.glob("af-event-*.json"))
        assert len(files) == 0

    def test_runner_passes_channel_to_pipeline(
        self, contract: ForgeContract, tmp_path: Path
    ) -> None:
        """ForgeRunner with a channel emits events for processed datasets."""
        events_dir = tmp_path / "events"
        channel = FileEventChannel(events_dir)
        registry = DatasetRegistry()
        registry.register(contract)
        runner = ForgeRunner(registry, event_channel=channel)

        source = _diverse_df()
        inputs = {"integ_ds": DatasetInput(source_df=source, forged_df=source.copy())}
        runner.run(inputs)

        files = list(events_dir.glob("af-event-*.json"))
        assert len(files) == 1


# ===========================================================================
# DriftReport tests (WBS 3.2)
# ===========================================================================


class TestDriftReport:
    """Tests for drift payload data shapes."""

    def test_from_dict(self) -> None:
        """DriftReport.from_dict() parses a DriftSentinel-shaped payload."""
        data = {
            "dataset_name": "sales",
            "health_score": 0.85,
            "columns_checked": 5,
            "columns_drifted": 1,
            "schema_match": True,
            "gate_verdict": "WARN",
            "column_reports": [
                {
                    "column": "revenue",
                    "baseline_score": 0.90,
                    "current_score": 0.55,
                    "delta": -0.35,
                    "classification": "COLLAPSED",
                }
            ],
        }
        report = DriftReport.from_dict(data)

        assert report.dataset_name == "sales"
        assert report.health_score == 0.85
        assert report.gate_verdict == "WARN"
        assert len(report.column_reports) == 1
        assert report.column_reports[0].classification == "COLLAPSED"

    def test_frozen(self) -> None:
        """DriftReport is immutable."""
        report = DriftReport.from_dict(
            {"dataset_name": "x", "gate_verdict": "PASS"}
        )
        with pytest.raises(AttributeError):
            report.dataset_name = "y"  # type: ignore[misc]

    def test_column_drift_report_frozen(self) -> None:
        """ColumnDriftReport is immutable."""
        cr = ColumnDriftReport(
            column="a",
            baseline_score=0.9,
            current_score=0.5,
            delta=-0.4,
            classification="COLLAPSED",
        )
        with pytest.raises(AttributeError):
            cr.column = "b"  # type: ignore[misc]

    def test_from_dict_defaults(self) -> None:
        """Missing fields get safe defaults."""
        report = DriftReport.from_dict({})

        assert report.dataset_name == ""
        assert report.health_score == 0.0
        assert report.gate_verdict == "PASS"
        assert report.schema_match is True
        assert len(report.column_reports) == 0


# ===========================================================================
# RemediationAction tests (WBS 3.2)
# ===========================================================================


class TestRemediationAction:
    """Tests for remediation action data shapes."""

    def test_frozen(self) -> None:
        """RemediationAction is immutable."""
        action = RemediationAction(
            dataset_name="x",
            drift_health_score=0.5,
            drift_gate_verdict="FAIL",
            action="re_score",
            reason="test",
            actioned_at="2026-01-01T00:00:00",
        )
        with pytest.raises(AttributeError):
            action.action = "skip"  # type: ignore[misc]

    def test_as_dict(self) -> None:
        """as_dict() returns expected keys."""
        action = RemediationAction(
            dataset_name="x",
            drift_health_score=0.5,
            drift_gate_verdict="FAIL",
            action="re_score",
            reason="test",
            actioned_at="2026-01-01T00:00:00",
        )
        d = action.as_dict()

        assert d["event"] == "remediation_action"
        assert d["action"] == "re_score"
        assert d["dataset_name"] == "x"


# ===========================================================================
# DriftIngester tests (WBS 3.2)
# ===========================================================================


class TestDriftIngester:
    """Tests for the drift ingestion routing engine."""

    @pytest.fixture()
    def registry(self, contract: ForgeContract) -> DatasetRegistry:
        reg = DatasetRegistry()
        reg.register(contract)
        return reg

    def _write_drift_file(
        self, drift_dir: Path, dataset_name: str, gate_verdict: str
    ) -> Path:
        """Write a drift report JSON file."""
        drift_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "dataset_name": dataset_name,
            "health_score": 0.60,
            "columns_checked": 3,
            "columns_drifted": 1,
            "schema_match": True,
            "gate_verdict": gate_verdict,
        }
        path = drift_dir / f"ds-drift-{dataset_name}.json"
        path.write_text(json.dumps(payload))
        return path

    def test_scan_reads_files(
        self, registry: DatasetRegistry, tmp_path: Path
    ) -> None:
        """scan() reads all ds-drift-*.json files."""
        drift_dir = tmp_path / "drift"
        self._write_drift_file(drift_dir, "integ_ds", "WARN")
        ingester = DriftIngester(drift_dir, registry)

        reports = ingester.scan()

        assert len(reports) == 1
        assert reports[0].dataset_name == "integ_ds"

    def test_scan_empty_directory(
        self, registry: DatasetRegistry, tmp_path: Path
    ) -> None:
        """scan() returns empty list when no files exist."""
        drift_dir = tmp_path / "drift"
        ingester = DriftIngester(drift_dir, registry)

        reports = ingester.scan()

        assert reports == []

    def test_ingest_registered_warn(
        self, registry: DatasetRegistry, tmp_path: Path
    ) -> None:
        """WARN verdict for a registered dataset produces re_score."""
        drift_dir = tmp_path / "drift"
        ingester = DriftIngester(drift_dir, registry)
        report = DriftReport.from_dict(
            {"dataset_name": "integ_ds", "gate_verdict": "WARN", "health_score": 0.6}
        )

        action = ingester.ingest(report)

        assert action.action == "re_score"
        assert action.dataset_name == "integ_ds"

    def test_ingest_registered_fail(
        self, registry: DatasetRegistry, tmp_path: Path
    ) -> None:
        """FAIL verdict for a registered dataset produces re_score."""
        drift_dir = tmp_path / "drift"
        ingester = DriftIngester(drift_dir, registry)
        report = DriftReport.from_dict(
            {"dataset_name": "integ_ds", "gate_verdict": "FAIL", "health_score": 0.3}
        )

        action = ingester.ingest(report)

        assert action.action == "re_score"

    def test_ingest_registered_pass(
        self, registry: DatasetRegistry, tmp_path: Path
    ) -> None:
        """PASS verdict produces flag_only."""
        drift_dir = tmp_path / "drift"
        ingester = DriftIngester(drift_dir, registry)
        report = DriftReport.from_dict(
            {"dataset_name": "integ_ds", "gate_verdict": "PASS", "health_score": 0.9}
        )

        action = ingester.ingest(report)

        assert action.action == "flag_only"

    def test_ingest_unknown_dataset(
        self, registry: DatasetRegistry, tmp_path: Path
    ) -> None:
        """Unknown dataset produces skip without error."""
        drift_dir = tmp_path / "drift"
        ingester = DriftIngester(drift_dir, registry)
        report = DriftReport.from_dict(
            {"dataset_name": "unknown_ds", "gate_verdict": "FAIL", "health_score": 0.1}
        )

        action = ingester.ingest(report)

        assert action.action == "skip"
        assert "not registered" in action.reason

    def test_ingest_writes_evidence(
        self, registry: DatasetRegistry, tmp_path: Path
    ) -> None:
        """When evidence_writer is provided, remediation actions are recorded."""
        drift_dir = tmp_path / "drift"
        evidence_dir = tmp_path / "evidence"
        writer = EvidenceWriter(evidence_dir)
        ingester = DriftIngester(drift_dir, registry, evidence_writer=writer)
        report = DriftReport.from_dict(
            {"dataset_name": "integ_ds", "gate_verdict": "WARN", "health_score": 0.5}
        )

        ingester.ingest(report)

        files = list(evidence_dir.glob("forge-evidence-*.json"))
        assert len(files) == 1
        payload = json.loads(files[0].read_text())
        assert payload["event"] == "remediation_action"

    def test_ingest_all_processes_and_renames(
        self, registry: DatasetRegistry, tmp_path: Path
    ) -> None:
        """ingest_all() processes files and renames them to .processed."""
        drift_dir = tmp_path / "drift"
        self._write_drift_file(drift_dir, "integ_ds", "WARN")
        ingester = DriftIngester(drift_dir, registry)

        actions = ingester.ingest_all()

        assert len(actions) == 1
        assert actions[0].action == "re_score"
        # Original file should be renamed
        assert len(list(drift_dir.glob("ds-drift-*.json"))) == 0
        assert len(list(drift_dir.glob("*.processed"))) == 1


# ===========================================================================
# Standalone-mode verification (AF-NFR-011, AF-SNFR-011)
# ===========================================================================


class TestStandaloneMode:
    """Prove standalone mode works with zero integration overhead."""

    def test_pipeline_standalone_no_errors(
        self, contract: ForgeContract
    ) -> None:
        """ForgePipeline with no event_channel runs without integration errors."""
        pipeline = ForgePipeline(contract)
        source = _diverse_df()

        result = pipeline.run(source, source.copy())

        assert result.pipeline_verdict in {"PASS", "WARN", "FAIL"}

    def test_runner_standalone_no_errors(
        self, contract: ForgeContract
    ) -> None:
        """ForgeRunner with no event_channel runs batch without errors."""
        registry = DatasetRegistry()
        registry.register(contract)
        runner = ForgeRunner(registry)
        source = _diverse_df()
        inputs = {"integ_ds": DatasetInput(source_df=source, forged_df=source.copy())}

        result = runner.run(inputs)

        assert result.batch_verdict in {"PASS", "WARN", "FAIL"}

    def test_null_channel_used_as_default(self) -> None:
        """NullEventChannel can substitute for any EventChannel."""
        channel = NullEventChannel()
        assert isinstance(channel, EventChannel)
