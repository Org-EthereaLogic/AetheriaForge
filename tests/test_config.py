"""Tests for forge contract loading and policy configuration.

Traces: AF-SR-006, AF-FR-004
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from aetheriaforge.config import ForgeContract


def _minimal_contract_data() -> dict[str, object]:
    """Return a minimal valid forge contract dictionary."""
    return {
        "dataset": {"name": "test_ds", "version": "1.0.0"},
        "source": {"catalog": "cat", "schema": "bronze", "table": "raw"},
        "target": {"catalog": "cat", "schema": "silver", "table": "forged"},
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


def test_load_forge_contract(tmp_path: Path) -> None:
    """A YAML contract file loads into a ForgeContract with correct fields."""
    data = _minimal_contract_data()
    path = tmp_path / "contract.yml"
    path.write_text(yaml.dump(data))

    contract = ForgeContract.from_yaml(path)

    assert contract.dataset_name == "test_ds"
    assert contract.source_table == "raw"
    assert contract.target_table == "forged"
    assert contract.resolution_enabled is False


def test_threshold_for_layer() -> None:
    """threshold_for_layer returns correct thresholds per Medallion layer."""
    contract = ForgeContract.from_dict(_minimal_contract_data())

    assert contract.threshold_for_layer("bronze") == 0.5
    assert contract.threshold_for_layer("silver") == 0.75
    assert contract.threshold_for_layer("gold") == 0.95


def test_threshold_unknown_layer_raises() -> None:
    """An unrecognized layer name raises ValueError."""
    contract = ForgeContract.from_dict(_minimal_contract_data())

    with pytest.raises(ValueError, match="Unknown layer"):
        contract.threshold_for_layer("platinum")


def test_missing_dataset_section_raises() -> None:
    """Omitting the 'dataset' section raises ValueError."""
    data = _minimal_contract_data()
    del data["dataset"]  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="missing required section"):
        ForgeContract.from_dict(data)


def test_template_contract_loads() -> None:
    """The shipped forge_contract.yml template parses without error."""
    from aetheriaforge.paths import repo_root

    template_path = repo_root() / "templates" / "forge_contract.yml"
    contract = ForgeContract.from_yaml(template_path)

    assert contract.dataset_name == "example_dataset"
