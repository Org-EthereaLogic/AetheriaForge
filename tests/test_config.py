"""Tests for forge contract loading and policy configuration.

Traces: AF-SR-006, AF-FR-004
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
import yaml

from aetheriaforge.config import ForgeContract
from aetheriaforge.schema import SchemaContract


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


def test_loads_referenced_schema_contract(tmp_path: Path) -> None:
    """A forge contract can resolve a relative schema contract path."""
    schema_path = tmp_path / "schema_contract.yml"
    schema_path.write_text(
        yaml.safe_dump(
            {
                "contract": {"name": "schema", "version": "2.1.0", "layer": "silver"},
                "columns": [{"name": "id", "type": "long", "nullable": False}],
                "enforcement": {"unknown_columns": "ignore"},
            },
            sort_keys=False,
        )
    )

    data = _minimal_contract_data()
    data["schema_contract"] = {  # type: ignore[index]
        "path": "schema_contract.yml",
        "enforce": True,
        "evolution": "versioned",
        "coerce_types": True,
    }
    contract_path = tmp_path / "forge_contract.yml"
    contract_path.write_text(yaml.safe_dump(data, sort_keys=False))

    contract = ForgeContract.from_yaml(contract_path)
    schema_contract = contract.load_schema_contract()

    assert isinstance(schema_contract, SchemaContract)
    assert schema_contract.version == "2.1.0"
    assert schema_contract.columns[0].name == "id"


def test_inline_schema_contract_reuses_dataset_version_defaults() -> None:
    """Inline schema contracts inherit dataset metadata when contract block is omitted."""
    data = _minimal_contract_data()
    data["schema_contract"] = {  # type: ignore[index]
        "enforce": True,
        "evolution": "versioned",
        "coerce_types": True,
        "columns": [{"name": "id", "type": "long", "nullable": False}],
    }

    contract = ForgeContract.from_dict(data)
    schema_contract = contract.load_schema_contract()

    assert schema_contract is not None
    assert schema_contract.version == "1.0.0"
    assert schema_contract.name == "test_ds_schema"


def test_loads_referenced_resolution_policy(tmp_path: Path) -> None:
    """A forge contract can resolve a relative resolution policy path."""
    policy_path = tmp_path / "resolution_policy.yml"
    policy_path.write_text(
        yaml.safe_dump(
            {
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
            sort_keys=False,
        )
    )

    data = _minimal_contract_data()
    data["resolution"] = {  # type: ignore[index]
        "enabled": True,
        "policy_path": "resolution_policy.yml",
    }
    contract_path = tmp_path / "forge_contract.yml"
    contract_path.write_text(yaml.safe_dump(data, sort_keys=False))

    contract = ForgeContract.from_yaml(contract_path)
    policy = contract.load_resolution_policy()

    assert policy is not None
    assert policy.policy_name == "resolve"


def test_builds_temporal_config_from_contract() -> None:
    """Temporal config can be derived from inline forge contract config."""
    data = _minimal_contract_data()
    data["temporal"] = {  # type: ignore[index]
        "enabled": True,
        "timestamp_column": "updated_at",
        "merge_strategy": "latest_wins",
        "conflict_behavior": "record_and_warn",
        "entity_key_columns": ["id"],
    }

    contract = ForgeContract.from_dict(data)
    temporal = contract.load_temporal_config()

    assert temporal is not None
    assert temporal.timestamp_column == "updated_at"


def test_null_options_normalize_to_empty_dict() -> None:
    """Optional source/target options accept explicit null YAML values."""
    data = _minimal_contract_data()
    source = cast(dict[str, object], data["source"])
    target = cast(dict[str, object], data["target"])
    data["source"] = {**source, "options": None}
    data["target"] = {**target, "options": None}

    contract = ForgeContract.from_dict(data)

    assert contract.source_options == {}
    assert contract.target_options == {}


def test_invalid_options_type_raises() -> None:
    """Non-mapping options fail closed with a clear contract error."""
    data = _minimal_contract_data()
    source = cast(dict[str, object], data["source"])
    data["source"] = {**source, "options": "bad"}

    with pytest.raises(ValueError, match="source.options"):
        ForgeContract.from_dict(data)


def test_mapping_options_are_preserved() -> None:
    """Mapping-valued source/target options are retained verbatim."""
    data = _minimal_contract_data()
    source = cast(dict[str, object], data["source"])
    target = cast(dict[str, object], data["target"])
    data["source"] = {**source, "options": {"header": True}}
    data["target"] = {**target, "options": {"mode": "overwrite"}}

    contract = ForgeContract.from_dict(data)

    assert contract.source_options == {"header": True}
    assert contract.target_options == {"mode": "overwrite"}


def test_resolve_relative_path_uses_repo_root_when_unloaded() -> None:
    """Relative paths fall back to repo_root when no source file path is known."""
    contract = ForgeContract.from_dict(_minimal_contract_data())

    resolved = contract.resolve_relative_path("templates/forge_contract.yml")

    assert resolved == Path.cwd() / "templates" / "forge_contract.yml"


def test_resolve_relative_path_preserves_absolute_paths() -> None:
    """Absolute path references are returned unchanged."""
    contract = ForgeContract.from_dict(_minimal_contract_data())
    absolute = Path("/tmp/aetheriaforge.yml")

    assert contract.resolve_relative_path(str(absolute)) == absolute


def test_load_temporal_config_returns_none_when_incomplete() -> None:
    """Incomplete inline temporal config is ignored rather than half-applied."""
    data = _minimal_contract_data()
    data["temporal"] = {  # type: ignore[index]
        "enabled": True,
        "merge_strategy": "latest_wins",
    }

    contract = ForgeContract.from_dict(data)

    assert contract.load_temporal_config() is None


def test_schema_contract_requires_columns_section() -> None:
    """SchemaContract validation fails closed when columns are missing."""
    with pytest.raises(ValueError, match="missing required section"):
        SchemaContract.from_dict({"contract": {"name": "schema"}})


def test_schema_contract_rejects_invalid_transform_shape() -> None:
    """Transform steps must be mappings with an explicit op."""
    with pytest.raises(ValueError, match="expected a mapping"):
        SchemaContract.from_dict(
            {
                "contract": {"name": "schema", "version": "1.0.0"},
                "columns": [
                    {
                        "name": "name",
                        "type": "string",
                        "transforms": ["upper"],
                    }
                ],
            }
        )

    with pytest.raises(ValueError, match="required transform key 'op'"):
        SchemaContract.from_dict(
            {
                "contract": {"name": "schema", "version": "1.0.0"},
                "columns": [
                    {
                        "name": "name",
                        "type": "string",
                        "transforms": [{"value": "upper"}],
                    }
                ],
            }
        )
