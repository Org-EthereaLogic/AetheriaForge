"""Schema contract loading for target-shape transformation and enforcement."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from aetheriaforge.schema.enforcer import ColumnSpec


@dataclass(frozen=True)
class TransformStep:
    """One transformation operation applied to a derived column."""

    op: str
    value: Any | None = None
    sources: tuple[str, ...] = ()
    separator: str = " "


@dataclass(frozen=True)
class SchemaColumn:
    """One target column definition from a schema contract."""

    name: str
    dtype: str
    nullable: bool
    source: str | None = None
    default: Any | None = None
    has_default: bool = False
    transforms: tuple[TransformStep, ...] = ()


@dataclass(frozen=True)
class SchemaEnforcementPolicy:
    """Enforcement preferences from the schema contract."""

    unknown_columns: str = "ignore"
    type_coercion: bool = True
    null_violation: str = "quarantine"


@dataclass(frozen=True)
class SchemaContract:
    """Resolved schema contract for transformation and enforcement."""

    name: str
    version: str
    layer: str
    columns: tuple[SchemaColumn, ...] = field(default_factory=tuple)
    enforcement: SchemaEnforcementPolicy = field(
        default_factory=SchemaEnforcementPolicy
    )
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: Path) -> SchemaContract:
        """Load a schema contract from disk."""
        with open(path) as fh:
            data = yaml.safe_load(fh)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SchemaContract:
        """Build a schema contract from a parsed dictionary."""
        for section in ("contract", "columns"):
            if section not in data:
                msg = f"Schema contract missing required section: '{section}'"
                raise ValueError(msg)

        contract = data["contract"]
        columns_raw = data["columns"]
        enforcement_raw = data.get("enforcement", {})

        columns: list[SchemaColumn] = []
        for column_index, column in enumerate(columns_raw):
            transforms_raw = column.get("transforms", [])
            column_context = (
                f"column '{column['name']}'"
                if "name" in column and column["name"] is not None
                else f"column at index {column_index}"
            )
            transforms_list: list[TransformStep] = []
            for step_index, step in enumerate(transforms_raw):
                if not isinstance(step, dict):
                    msg = (
                        "Schema contract has invalid transform step for "
                        f"{column_context} at step index {step_index}: "
                        "expected a mapping"
                    )
                    raise ValueError(msg)
                if "op" not in step:
                    msg = (
                        "Schema contract missing required transform key 'op' for "
                        f"{column_context} at step index {step_index}"
                    )
                    raise ValueError(msg)
                transforms_list.append(
                    TransformStep(
                        op=str(step["op"]),
                        value=step.get("value"),
                        sources=tuple(str(src) for src in step.get("sources", [])),
                        separator=str(step.get("separator", " ")),
                    )
                )
            transforms = tuple(transforms_list)
            columns.append(
                SchemaColumn(
                    name=str(column["name"]),
                    dtype=str(column.get("type", "string")),
                    nullable=bool(column.get("nullable", True)),
                    source=(
                        str(column["source"])
                        if "source" in column and column["source"] is not None
                        else None
                    ),
                    default=column.get("default"),
                    has_default="default" in column,
                    transforms=transforms,
                )
            )

        return cls(
            name=str(contract.get("name", "schema_contract")),
            version=str(contract.get("version", "0.0.0")),
            layer=str(contract.get("layer", "silver")),
            columns=tuple(columns),
            enforcement=SchemaEnforcementPolicy(
                unknown_columns=str(enforcement_raw.get("unknown_columns", "ignore")),
                type_coercion=bool(enforcement_raw.get("type_coercion", True)),
                null_violation=str(
                    enforcement_raw.get("null_violation", "quarantine")
                ),
            ),
            raw=data,
        )

    def to_column_specs(self) -> list[ColumnSpec]:
        """Convert this schema contract into enforcer column specs."""
        from aetheriaforge.schema.enforcer import ColumnSpec

        return [
            ColumnSpec(name=column.name, dtype=column.dtype, nullable=column.nullable)
            for column in self.columns
        ]
