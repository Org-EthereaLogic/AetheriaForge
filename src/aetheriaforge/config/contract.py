"""Forge contract and policy configuration loaded from YAML."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml  # type: ignore[import-untyped]

from aetheriaforge.paths import repo_root

if TYPE_CHECKING:
    from aetheriaforge.resolution.policy import ResolutionPolicy
    from aetheriaforge.schema.contract import SchemaContract
    from aetheriaforge.temporal.reconciler import TemporalConfig


def _options_mapping(raw: Any, *, field_name: str) -> dict[str, Any]:
    """Normalize optional options mappings from YAML."""
    if raw is None:
        return {}
    if isinstance(raw, Mapping):
        return dict(raw)
    msg = f"Forge contract field '{field_name}' must be a mapping when provided"
    raise ValueError(msg)


def _parse_coherence(coh: dict[str, Any]) -> CoherenceConfig:
    """Build a :class:`CoherenceConfig` from a raw YAML mapping."""
    thresholds = coh.get("thresholds", {})
    return CoherenceConfig(
        engine=coh.get("engine", "shannon"),
        bronze_min=float(thresholds.get("bronze_min", 0.5)),
        silver_min=float(thresholds.get("silver_min", 0.75)),
        gold_min=float(thresholds.get("gold_min", 0.95)),
    )


def _parse_schema_contract_config(sc: dict[str, Any]) -> SchemaContractConfig:
    """Build a :class:`SchemaContractConfig` from a raw YAML mapping."""
    return SchemaContractConfig(
        enforce=bool(sc.get("enforce", True)),
        evolution=str(sc.get("evolution", "versioned")),
        coerce_types=bool(sc.get("coerce_types", True)),
        path=str(sc.get("path", "")),
        unknown_columns=str(sc.get("unknown_columns", "ignore")),
        null_violation=str(sc.get("null_violation", "quarantine")),
    )


@dataclass(frozen=True)
class CoherenceConfig:
    """Coherence scoring configuration from a forge contract."""

    engine: str
    bronze_min: float
    silver_min: float
    gold_min: float

    def threshold_for_layer(self, layer: str) -> float:
        """Return the coherence threshold for the given Medallion layer."""
        thresholds = {
            "bronze": self.bronze_min,
            "silver": self.silver_min,
            "gold": self.gold_min,
        }
        if layer not in thresholds:
            msg = f"Unknown layer: {layer!r}"
            raise ValueError(msg)
        return thresholds[layer]


@dataclass(frozen=True)
class SchemaContractConfig:
    """Schema enforcement configuration from a forge contract."""

    enforce: bool
    evolution: str
    coerce_types: bool
    path: str = ""
    unknown_columns: str = "ignore"
    null_violation: str = "quarantine"


@dataclass(frozen=True)
class ForgeContract:
    """Immutable representation of a forge contract loaded from YAML."""

    dataset_name: str
    dataset_version: str
    source_catalog: str
    source_schema: str
    source_table: str
    source_path: str
    source_format: str
    source_options: dict[str, Any]
    target_catalog: str
    target_schema: str
    target_table: str
    target_path: str
    target_format: str
    target_options: dict[str, Any]
    coherence: CoherenceConfig
    schema_contract: SchemaContractConfig
    resolution_enabled: bool = False
    temporal_enabled: bool = False
    loaded_from: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def threshold_for_layer(self, layer: str) -> float:
        """Delegate to CoherenceConfig for the given Medallion layer threshold."""
        return self.coherence.threshold_for_layer(layer)

    @classmethod
    def from_yaml(cls, path: Path) -> ForgeContract:
        """Load a ForgeContract from a YAML file on disk."""
        with open(path) as fh:
            data = yaml.safe_load(fh)
        return cls.from_dict(data, loaded_from=path)

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        loaded_from: Path | None = None,
    ) -> ForgeContract:
        """Construct a ForgeContract from a parsed YAML dictionary."""
        for section in ("dataset", "source", "target", "coherence", "schema_contract"):
            if section not in data:
                msg = f"Forge contract missing required section: '{section}'"
                raise ValueError(msg)

        ds = data["dataset"]
        src = data["source"]
        tgt = data["target"]
        resolution = data.get("resolution", {})
        temporal = data.get("temporal", {})

        return cls(
            dataset_name=str(ds["name"]),
            dataset_version=str(ds.get("version", "0.0.0")),
            source_catalog=str(src.get("catalog", "")),
            source_schema=str(src.get("schema", "")),
            source_table=str(src.get("table", "")),
            source_path=str(src.get("path", "")),
            source_format=str(src.get("format", "")),
            source_options=_options_mapping(
                src.get("options"),
                field_name="source.options",
            ),
            target_catalog=str(tgt.get("catalog", "")),
            target_schema=str(tgt.get("schema", "")),
            target_table=str(tgt.get("table", "")),
            target_path=str(tgt.get("path", "")),
            target_format=str(tgt.get("format", "")),
            target_options=_options_mapping(
                tgt.get("options"),
                field_name="target.options",
            ),
            coherence=_parse_coherence(data["coherence"]),
            schema_contract=_parse_schema_contract_config(data["schema_contract"]),
            resolution_enabled=bool(resolution.get("enabled", False)),
            temporal_enabled=bool(temporal.get("enabled", False)),
            loaded_from=str(loaded_from) if loaded_from is not None else "",
            raw=data,
        )

    def resolve_relative_path(self, reference: str) -> Path:
        """Resolve *reference* relative to the loaded contract path or repo root."""
        candidate = Path(reference)
        if candidate.is_absolute():
            return candidate
        if self.loaded_from:
            return Path(self.loaded_from).resolve().parent / candidate
        root: Path = repo_root()
        return root / candidate

    def load_schema_contract(self) -> SchemaContract | None:
        """Load the referenced schema contract, if one is configured."""
        from aetheriaforge.schema.contract import SchemaContract

        section = self.raw.get("schema_contract", {})
        if not isinstance(section, dict):
            return None

        path = str(section.get("path", "")).strip()
        if path:
            return SchemaContract.from_yaml(self.resolve_relative_path(path))

        if "columns" in section:
            inline: dict[str, Any] = {
                "contract": section.get(
                    "contract",
                    {
                        "name": f"{self.dataset_name}_schema",
                        "version": self.dataset_version,
                        "layer": self.target_schema or "silver",
                    },
                ),
                "columns": section.get("columns", []),
            }
            if "enforcement" in section:
                inline["enforcement"] = section.get("enforcement", {})
            return SchemaContract.from_dict(inline)

        return None

    def load_resolution_policy(self) -> ResolutionPolicy | None:
        """Load the referenced resolution policy, if one is configured."""
        from aetheriaforge.resolution.policy import ResolutionPolicy

        section = self.raw.get("resolution", {})
        if not isinstance(section, dict):
            return None

        path = str(section.get("policy_path", "")).strip()
        if path:
            return ResolutionPolicy.from_yaml(self.resolve_relative_path(path))

        if all(key in section for key in ("policy", "sources", "matching", "evidence")):
            return ResolutionPolicy.from_dict(section)

        return None

    def load_temporal_config(self) -> TemporalConfig | None:
        """Build a temporal config from inline contract fields, if configured."""
        from aetheriaforge.temporal.reconciler import TemporalConfig

        section = self.raw.get("temporal", {})
        if not isinstance(section, dict) or not section.get("enabled", False):
            return None

        entity_keys = tuple(str(key) for key in section.get("entity_key_columns", ()))
        timestamp_column = str(section.get("timestamp_column", ""))
        if not timestamp_column or not entity_keys:
            return None

        return TemporalConfig(
            timestamp_column=timestamp_column,
            merge_strategy=str(section.get("merge_strategy", "latest_wins")),
            conflict_behavior=str(
                section.get("conflict_behavior", "record_and_warn")
            ),
            entity_key_columns=entity_keys,
        )

    def resolution_secondary_source(self) -> dict[str, Any] | None:
        """Return the configured secondary source descriptor for resolution."""
        section = self.raw.get("resolution", {})
        if not isinstance(section, dict):
            return None
        secondary = section.get("secondary_source")
        if isinstance(secondary, dict):
            return secondary
        return None
