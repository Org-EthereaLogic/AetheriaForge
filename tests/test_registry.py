"""Tests for the dataset registry.

Traces: AF-IP-004 section 1, AF-SDD-001 section 3
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from aetheriaforge.config import ForgeContract
from aetheriaforge.config.registry import DatasetRegistry


def _contract_dict(
    name: str = "ds_a", version: str = "1.0.0"
) -> dict[str, object]:
    """Return a minimal valid forge contract dictionary."""
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


def _make_contract(
    name: str = "ds_a", version: str = "1.0.0"
) -> ForgeContract:
    return ForgeContract.from_dict(_contract_dict(name, version))


# -- register and get ---------------------------------------------------------


def test_register_and_get_latest() -> None:
    reg = DatasetRegistry()
    reg.register(_make_contract("ds_a", "1.0.0"))
    reg.register(_make_contract("ds_a", "2.0.0"))

    latest = reg.get("ds_a")
    assert latest.dataset_version == "2.0.0"


def test_get_specific_version() -> None:
    reg = DatasetRegistry()
    reg.register(_make_contract("ds_a", "1.0.0"))
    reg.register(_make_contract("ds_a", "2.0.0"))

    v1 = reg.get("ds_a", version="1.0.0")
    assert v1.dataset_version == "1.0.0"


def test_get_unknown_dataset_raises() -> None:
    reg = DatasetRegistry()
    with pytest.raises(KeyError, match="No contracts registered"):
        reg.get("nonexistent")


def test_get_unknown_version_raises() -> None:
    reg = DatasetRegistry()
    reg.register(_make_contract("ds_a", "1.0.0"))
    with pytest.raises(KeyError, match="Version"):
        reg.get("ds_a", version="9.9.9")


# -- duplicate rejection ------------------------------------------------------


def test_duplicate_registration_raises() -> None:
    reg = DatasetRegistry()
    reg.register(_make_contract("ds_a", "1.0.0"))
    with pytest.raises(ValueError, match="already registered"):
        reg.register(_make_contract("ds_a", "1.0.0"))


# -- listing ------------------------------------------------------------------


def test_list_datasets() -> None:
    reg = DatasetRegistry()
    reg.register(_make_contract("ds_b"))
    reg.register(_make_contract("ds_a"))

    assert reg.list_datasets() == ["ds_a", "ds_b"]


def test_list_versions_sorted() -> None:
    reg = DatasetRegistry()
    reg.register(_make_contract("ds_a", "2.0.0"))
    reg.register(_make_contract("ds_a", "1.0.0"))
    reg.register(_make_contract("ds_a", "1.1.0"))

    assert reg.list_versions("ds_a") == ["1.0.0", "1.1.0", "2.0.0"]


def test_list_versions_unknown_raises() -> None:
    reg = DatasetRegistry()
    with pytest.raises(KeyError):
        reg.list_versions("nope")


# -- len and contains --------------------------------------------------------


def test_len() -> None:
    reg = DatasetRegistry()
    assert len(reg) == 0
    reg.register(_make_contract("ds_a", "1.0.0"))
    reg.register(_make_contract("ds_a", "2.0.0"))
    reg.register(_make_contract("ds_b", "1.0.0"))
    assert len(reg) == 3


def test_contains() -> None:
    reg = DatasetRegistry()
    reg.register(_make_contract("ds_a"))
    assert "ds_a" in reg
    assert "ds_b" not in reg


# -- directory loading --------------------------------------------------------


def test_from_directory(tmp_path: Path) -> None:
    for name, version in [("alpha", "1.0.0"), ("beta", "2.0.0")]:
        data = _contract_dict(name, version)
        (tmp_path / f"{name}.yml").write_text(yaml.dump(data))

    reg = DatasetRegistry.from_directory(tmp_path)

    assert len(reg) == 2
    assert reg.get("alpha").dataset_version == "1.0.0"
    assert reg.get("beta").dataset_version == "2.0.0"


def test_from_directory_ignores_non_yaml(tmp_path: Path) -> None:
    data = _contract_dict("gamma", "1.0.0")
    (tmp_path / "gamma.yml").write_text(yaml.dump(data))
    (tmp_path / "README.md").write_text("not a contract")

    reg = DatasetRegistry.from_directory(tmp_path)
    assert len(reg) == 1


def test_from_directory_skips_malformed_yaml(tmp_path: Path) -> None:
    (tmp_path / "valid.yml").write_text(yaml.dump(_contract_dict("valid", "1.0.0")))
    (tmp_path / "broken.yml").write_text("dataset: [")

    reg = DatasetRegistry.from_directory(tmp_path)

    assert len(reg) == 1
    assert reg.get("valid").dataset_version == "1.0.0"


def test_from_directory_summarizes_malformed_warnings(
    tmp_path: Path, caplog: pytest.LogCaptureFixture,
) -> None:
    (tmp_path / "valid.yml").write_text(yaml.dump(_contract_dict("valid", "1.0.0")))
    (tmp_path / "broken_1.yml").write_text("dataset: [")
    (tmp_path / "broken_2.yml").write_text("dataset: [")

    with caplog.at_level("WARNING"):
        reg = DatasetRegistry.from_directory(tmp_path)

    assert len(reg) == 1
    warnings = [record.message for record in caplog.records]
    assert len(warnings) == 1
    assert "Skipped 2 malformed contract file(s)" in warnings[0]
    assert "broken_1.yml" in warnings[0]


def test_from_directory_sanitizes_log_values(
    tmp_path: Path, caplog: pytest.LogCaptureFixture,
) -> None:
    malicious_dir = tmp_path / "contracts\nforged"
    malicious_dir.mkdir()
    (malicious_dir / "broken.yml").write_text("dataset: [")

    with caplog.at_level("WARNING"):
        DatasetRegistry.from_directory(malicious_dir)

    assert len(caplog.records) == 1
    message = caplog.records[0].message
    assert "contracts\\nforged" in message
    assert "contracts\nforged" not in message
