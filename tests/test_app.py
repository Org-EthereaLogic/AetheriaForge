"""Tests for the AetheriaForge operator dashboard helper functions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

import app.app as app_module
from app.analytics import (
    build_analytics_data,
    build_coherence_histogram,
    build_coherence_trend,
    build_daily_volume,
    build_verdict_bar,
)

# -- Fixtures ----------------------------------------------------------------


def _make_contract_yaml(path: Path, name: str, version: str = "1.0.0") -> Path:
    """Write a minimal forge contract YAML file and return its path."""
    data = {
        "dataset": {"name": name, "version": version},
        "source": {"catalog": "src_cat", "schema": "src_sch", "table": f"{name}_raw"},
        "target": {"catalog": "tgt_cat", "schema": "tgt_sch", "table": f"{name}_clean"},
        "coherence": {
            "engine": "shannon",
            "thresholds": {"bronze_min": 0.5, "silver_min": 0.75, "gold_min": 0.95},
        },
        "schema_contract": {"enforce": True, "evolution": "versioned", "coerce_types": True},
    }
    filepath = path / f"{name}.yml"
    filepath.write_text(yaml.dump(data))
    return filepath


def _make_evidence_json(
    path: Path,
    name: str,
    verdict: str,
    score: float,
    execution_mode: str = "unverified",
) -> Path:
    """Write a minimal evidence artifact and return its path."""
    data = {
        "event": "pipeline_result",
        "dataset_name": name,
        "pipeline_verdict": verdict,
        "execution_mode": execution_mode,
        "source_location": "cat.bronze.raw",
        "target_location": "cat.silver.forged",
        "contract_version": "1.0.0",
        "run_at": "2026-04-03T14:00:00+00:00",
        "forge_result": {
            "coherence_score": score,
            "records_in": 100,
            "records_out": 95,
        },
    }
    filename = f"forge-evidence-20260403T140000_{name}.json"
    filepath = path / filename
    filepath.write_text(json.dumps(data))
    return filepath


# -- _fmt_timestamp ----------------------------------------------------------


class TestFmtTimestamp:
    def test_valid_iso(self) -> None:
        assert "Apr 03" in app_module._fmt_timestamp("2026-04-03T14:00:00+00:00")

    def test_empty_string(self) -> None:
        assert app_module._fmt_timestamp("") == ""

    def test_invalid_string(self) -> None:
        assert app_module._fmt_timestamp("not-a-date") == "not-a-date"


# -- _build_summary_line -----------------------------------------------------


class TestBuildSummaryLine:
    def test_empty_rows(self) -> None:
        assert _build_summary_line([]) == ""

    def test_no_artifacts_row(self) -> None:
        assert _build_summary_line([["(no artifacts found)", "", "", "", "", ""]]) == ""

    def test_valid_rows(self) -> None:
        rows = [
            ["f1.json", "ds_a", "\U0001f7e2 PASS", "\u2705 contract_backed", "0.85", "100 \u2192 95", "Apr 03"],
            ["f2.json", "ds_b", "\U0001f534 FAIL", "\u2753 unverified", "0.50", "100 \u2192 90", "Apr 03"],
        ]
        result = _build_summary_line(rows)
        assert "2 artifacts" in result
        assert "PASS: 1" in result
        assert "FAIL: 1" in result

    def test_truncation_row_does_not_count_as_other(self) -> None:
        rows = [
            ["f1.json", "ds_a", "\U0001f7e2 PASS", "\u2705 contract_backed", "0.85", "100 \u2192 95", "Apr 03"],
            ["f2.json", "ds_b", "\U0001f534 FAIL", "\u2753 unverified", "0.50", "100 \u2192 90", "Apr 03"],
            ["(Truncated from 1008 to latest 1000 records)", "...", "...", "...", "...", "...", "..."],
        ]
        result = _build_summary_line_with_total(rows, total_records=1008)
        assert "1008 artifacts" in result
        assert "other:" not in result


# -- load_registry_table -----------------------------------------------------


class TestLoadRegistryTable:
    def test_missing_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        missing = tmp_path / "contracts"
        monkeypatch.setattr(app_module, "CONTRACTS_DIR", str(missing))
        rows = load_registry_table(str(missing))
        assert "no contracts directory" in rows[0][0]

    def test_empty_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(app_module, "CONTRACTS_DIR", str(tmp_path))
        rows = load_registry_table(str(tmp_path))
        assert "no datasets" in rows[0][0]

    def test_valid_contracts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(app_module, "CONTRACTS_DIR", str(tmp_path))
        _make_contract_yaml(tmp_path, "orders")
        _make_contract_yaml(tmp_path, "customers")
        rows = load_registry_table(str(tmp_path))
        assert len(rows) == 2
        names = {row[0] for row in rows}
        assert names == {"orders", "customers"}

    def test_multiple_versions(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(app_module, "CONTRACTS_DIR", str(tmp_path))
        _make_contract_yaml(tmp_path, "orders", "1.0.0")
        _make_contract_yaml(tmp_path, "orders_v2", "2.0.0")
        # We use different names because same-name contracts need different YAML
        rows = load_registry_table(str(tmp_path))
        assert len(rows) == 2

    def test_rejects_untrusted_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        trusted = tmp_path / "trusted"
        untrusted = tmp_path / "untrusted"
        trusted.mkdir()
        untrusted.mkdir()
        monkeypatch.setattr(app_module, "CONTRACTS_DIR", str(trusted))
        rows = load_registry_table(str(untrusted))
        assert "must match the configured directory" in rows[0][0]


# -- query_evidence ----------------------------------------------------------


class TestQueryEvidence:
    def test_missing_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        missing = tmp_path / "evidence"
        monkeypatch.setattr(app_module, "EVIDENCE_DIR", str(missing))
        rows = query_evidence(str(missing), "", "", "", "")
        assert "no artifacts" in rows[0][0]

    def test_empty_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(app_module, "EVIDENCE_DIR", str(tmp_path))
        rows = query_evidence(str(tmp_path), "", "", "", "")
        assert "no artifacts" in rows[0][0]

    def test_returns_artifacts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(app_module, "EVIDENCE_DIR", str(tmp_path))
        _make_evidence_json(tmp_path, "orders", "PASS", 0.85)
        _make_evidence_json(tmp_path, "customers", "FAIL", 0.50)
        rows = query_evidence(str(tmp_path), "", "", "", "")
        assert len(rows) == 2

    def test_filter_by_dataset(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(app_module, "EVIDENCE_DIR", str(tmp_path))
        _make_evidence_json(tmp_path, "orders", "PASS", 0.85)
        _make_evidence_json(tmp_path, "customers", "FAIL", 0.50)
        rows = query_evidence(str(tmp_path), "orders", "", "", "")
        assert len(rows) == 1
        assert rows[0][1] == "orders"

    def test_filter_by_verdict(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(app_module, "EVIDENCE_DIR", str(tmp_path))
        _make_evidence_json(tmp_path, "orders", "PASS", 0.85)
        _make_evidence_json(tmp_path, "customers", "FAIL", 0.50)
        rows = query_evidence(str(tmp_path), "", "FAIL", "", "")
        assert len(rows) == 1
        assert "FAIL" in rows[0][2]

    def test_date_only_filters_are_timezone_safe(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(app_module, "EVIDENCE_DIR", str(tmp_path))
        _make_evidence_json(tmp_path, "orders", "PASS", 0.85)
        rows = query_evidence(str(tmp_path), "", "", "2026-04-03", "2026-04-03")
        assert len(rows) == 1
        assert rows[0][1] == "orders"

    def test_mode_column_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(app_module, "EVIDENCE_DIR", str(tmp_path))
        _make_evidence_json(tmp_path, "orders", "PASS", 0.85, execution_mode="demo")
        rows = query_evidence(str(tmp_path), "", "", "", "")
        assert len(rows) == 1
        # Mode is column index 3
        assert "demo" in rows[0][3]

    def test_contract_backed_mode_display(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(app_module, "EVIDENCE_DIR", str(tmp_path))
        _make_evidence_json(tmp_path, "orders", "PASS", 0.85, execution_mode="contract_backed")
        rows = query_evidence(str(tmp_path), "", "", "", "")
        assert "contract_backed" in rows[0][3]

    def test_rejects_untrusted_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        trusted = tmp_path / "trusted"
        untrusted = tmp_path / "untrusted"
        trusted.mkdir()
        untrusted.mkdir()
        monkeypatch.setattr(app_module, "EVIDENCE_DIR", str(trusted))
        rows = query_evidence(str(untrusted), "", "", "", "")
        assert "must match the configured directory" in rows[0][0]


# -- load_artifact_detail ----------------------------------------------------


class TestLoadArtifactDetail:
    def test_empty_filename(self) -> None:
        result = load_artifact_detail("/tmp", "")
        assert "select an artifact" in result

    def test_missing_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(app_module, "EVIDENCE_DIR", str(tmp_path))
        result = load_artifact_detail(str(tmp_path), "nonexistent.json")
        assert "file not found" in result

    def test_valid_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(app_module, "EVIDENCE_DIR", str(tmp_path))
        fp = _make_evidence_json(tmp_path, "orders", "PASS", 0.85)
        result = load_artifact_detail(str(tmp_path), fp.name)
        parsed = json.loads(result)
        assert parsed["dataset_name"] == "orders"

    def test_rejects_path_traversal_filename(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(app_module, "EVIDENCE_DIR", str(tmp_path))
        result = load_artifact_detail(str(tmp_path), "../secret.json")
        assert "bare filename" in result


# -- load_artifact_meta ------------------------------------------------------


class TestLoadArtifactMeta:
    def test_empty_filename(self) -> None:
        result = load_artifact_meta("/tmp", "")
        assert "Enter an artifact" in result

    def test_missing_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(app_module, "EVIDENCE_DIR", str(tmp_path))
        result = load_artifact_meta(str(tmp_path), "nonexistent.json")
        assert "not found" in result

    def test_valid_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(app_module, "EVIDENCE_DIR", str(tmp_path))
        fp = _make_evidence_json(tmp_path, "orders", "PASS", 0.85)
        result = load_artifact_meta(str(tmp_path), fp.name)
        assert "orders" in result
        assert "PASS" in result
        assert "0.85" in result
        # Provenance fields must appear in metadata display.
        assert "unverified" in result
        assert "cat.bronze.raw" in result
        assert "v1.0.0" in result

    def test_rejects_untrusted_evidence_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        trusted = tmp_path / "trusted"
        untrusted = tmp_path / "untrusted"
        trusted.mkdir()
        untrusted.mkdir()
        monkeypatch.setattr(app_module, "EVIDENCE_DIR", str(trusted))
        result = load_artifact_meta(str(untrusted), "artifact.json")
        assert "configured directory" in result


# -- build_analytics_data ----------------------------------------------------


class TestBuildAnalyticsData:
    def test_missing_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        missing = tmp_path / "evidence"
        monkeypatch.setattr(analytics_module, "DEFAULT_EVIDENCE_DIR", str(missing))
        assert build_analytics_data(str(missing)) == []

    def test_empty_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(analytics_module, "DEFAULT_EVIDENCE_DIR", str(tmp_path))
        assert build_analytics_data(str(tmp_path)) == []

    def test_loads_records(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(analytics_module, "DEFAULT_EVIDENCE_DIR", str(tmp_path))
        _make_evidence_json(tmp_path, "orders", "PASS", 0.85)
        _make_evidence_json(tmp_path, "customers", "FAIL", 0.50)
        records = build_analytics_data(str(tmp_path))
        assert len(records) == 2

    def test_skips_malformed_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(analytics_module, "DEFAULT_EVIDENCE_DIR", str(tmp_path))
        _make_evidence_json(tmp_path, "orders", "PASS", 0.85)
        (tmp_path / "bad.json").write_text("{not valid json")
        records = build_analytics_data(str(tmp_path))
        assert len(records) == 1

    def test_rejects_untrusted_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        trusted = tmp_path / "trusted"
        untrusted = tmp_path / "untrusted"
        trusted.mkdir()
        untrusted.mkdir()
        monkeypatch.setattr(analytics_module, "DEFAULT_EVIDENCE_DIR", str(trusted))
        assert build_analytics_data(str(untrusted)) == []


class TestLogoUris:
    def test_logo_variants_encode_as_data_uris(self) -> None:
        light_uri, dark_uri = _get_logo_uris()
        assert light_uri is not None
        assert dark_uri is not None
        assert light_uri.startswith("data:image/png;base64,")
        assert dark_uri.startswith("data:image/png;base64,")


# -- Chart builders ----------------------------------------------------------


@pytest.fixture()
def sample_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> list[dict]:
    """Create sample evidence files and return parsed records."""
    monkeypatch.setattr(analytics_module, "DEFAULT_EVIDENCE_DIR", str(tmp_path))
    _make_evidence_json(tmp_path, "orders", "PASS", 0.85)
    _make_evidence_json(tmp_path, "customers", "FAIL", 0.50)
    _make_evidence_json(tmp_path, "products", "WARN", 0.72)
    return build_analytics_data(str(tmp_path))


class TestVerdictBar:
    def test_returns_figure(self, sample_records: list[dict]) -> None:
        fig = build_verdict_bar(sample_records)
        assert fig is not None
        assert hasattr(fig, "data")

    def test_themes(self, sample_records: list[dict]) -> None:
        for theme in (
            "Brand",
            "Traffic Light",
            "Colorblind Safe",
            "Cyberpunk",
            "Pastel",
        ):
            fig = build_verdict_bar(sample_records, theme)
            assert fig is not None


class TestCoherenceHistogram:
    def test_returns_figure(self, sample_records: list[dict]) -> None:
        fig = build_coherence_histogram(sample_records)
        assert fig is not None


class TestDailyVolume:
    def test_returns_figure(self, sample_records: list[dict]) -> None:
        fig = build_daily_volume(sample_records)
        assert fig is not None
        assert fig.layout.xaxis.type == "category"


class TestCoherenceTrend:
    def test_returns_figure(self, sample_records: list[dict]) -> None:
        fig = build_coherence_trend(sample_records)
        assert fig is not None
        assert fig.layout.xaxis.type == "category"

    def test_empty_records(self) -> None:
        fig = build_coherence_trend([])
        assert fig is not None
