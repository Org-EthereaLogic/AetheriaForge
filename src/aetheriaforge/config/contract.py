"""Forge contract and policy configuration loaded from YAML."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


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


@dataclass(frozen=True)
class ForgeContract:
    """Immutable representation of a forge contract loaded from YAML."""

    dataset_name: str
    dataset_version: str
    source_catalog: str
    source_schema: str
    source_table: str
    target_catalog: str
    target_schema: str
    target_table: str
    coherence: CoherenceConfig
    schema_contract: SchemaContractConfig
    resolution_enabled: bool = False
    temporal_enabled: bool = False
    raw: dict[str, Any] = field(default_factory=dict)

    def threshold_for_layer(self, layer: str) -> float:
        """Delegate to CoherenceConfig for the given Medallion layer threshold."""
        return self.coherence.threshold_for_layer(layer)

    @classmethod
    def from_yaml(cls, path: Path) -> ForgeContract:
        """Load a ForgeContract from a YAML file on disk."""
        with open(path) as fh:
            data = yaml.safe_load(fh)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ForgeContract:
        """Construct a ForgeContract from a parsed YAML dictionary."""
        for section in ("dataset", "source", "target", "coherence", "schema_contract"):
            if section not in data:
                msg = f"Forge contract missing required section: '{section}'"
                raise ValueError(msg)

        ds = data["dataset"]
        src = data["source"]
        tgt = data["target"]
        coh = data["coherence"]
        thresholds = coh.get("thresholds", {})
        sc = data["schema_contract"]

        coherence = CoherenceConfig(
            engine=coh.get("engine", "shannon"),
            bronze_min=float(thresholds.get("bronze_min", 0.5)),
            silver_min=float(thresholds.get("silver_min", 0.75)),
            gold_min=float(thresholds.get("gold_min", 0.95)),
        )

        schema_contract = SchemaContractConfig(
            enforce=bool(sc.get("enforce", True)),
            evolution=str(sc.get("evolution", "versioned")),
            coerce_types=bool(sc.get("coerce_types", True)),
        )

        resolution = data.get("resolution", {})
        temporal = data.get("temporal", {})

        return cls(
            dataset_name=str(ds["name"]),
            dataset_version=str(ds.get("version", "0.0.0")),
            source_catalog=str(src.get("catalog", "")),
            source_schema=str(src.get("schema", "")),
            source_table=str(src.get("table", "")),
            target_catalog=str(tgt.get("catalog", "")),
            target_schema=str(tgt.get("schema", "")),
            target_table=str(tgt.get("table", "")),
            coherence=coherence,
            schema_contract=schema_contract,
            resolution_enabled=bool(resolution.get("enabled", False)),
            temporal_enabled=bool(temporal.get("enabled", False)),
            raw=data,
        )
