"""Schema contract loading for target-shape transformation and enforcement."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml  # type: ignore[import-untyped]

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


def _column_context(column: dict[str, Any], column_index: int) -> str:
    """Return a human-readable label for a column in error messages."""
    if "name" in column and column["name"] is not None:
        return f"column '{column['name']}'"
    return f"column at index {column_index}"


def _parse_transform_step(
    step: Any,
    *,
    column_context: str,
    step_index: int,
) -> TransformStep:
    """Validate and build a :class:`TransformStep` from a raw YAML entry."""
    if not isinstance(step, dict):
        msg = (
            "Schema contract has invalid transform step for "
            f"{column_context} at step index {step_index}: expected a mapping"
        )
        raise ValueError(msg)
    if "op" not in step:
        msg = (
            "Schema contract missing required transform key 'op' for "
            f"{column_context} at step index {step_index}"
        )
        raise ValueError(msg)
    return TransformStep(
        op=str(step["op"]),
        value=step.get("value"),
        sources=tuple(str(src) for src in step.get("sources", [])),
        separator=str(step.get("separator", " ")),
    )


def _parse_column(column: dict[str, Any], column_index: int) -> SchemaColumn:
    """Validate and build a :class:`SchemaColumn` from a raw YAML entry."""
    column_context = _column_context(column, column_index)
    transforms = tuple(
        _parse_transform_step(
            step,
            column_context=column_context,
            step_index=step_index,
        )
        for step_index, step in enumerate(column.get("transforms", []))
    )
    source = (
        str(column["source"])
        if "source" in column and column["source"] is not None
        else None
    )
    return SchemaColumn(
        name=str(column["name"]),
        dtype=str(column.get("type", "string")),
        nullable=bool(column.get("nullable", True)),
        source=source,
        default=column.get("default"),
        has_default="default" in column,
        transforms=transforms,
    )


def _parse_enforcement(
    enforcement_raw: dict[str, Any],
) -> SchemaEnforcementPolicy:
    """Build a :class:`SchemaEnforcementPolicy` from a raw YAML mapping."""
    return SchemaEnforcementPolicy(
        unknown_columns=str(enforcement_raw.get("unknown_columns", "ignore")),
        type_coercion=bool(enforcement_raw.get("type_coercion", True)),
        null_violation=str(enforcement_raw.get("null_violation", "quarantine")),
    )


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
        columns = tuple(
            _parse_column(column, column_index)
            for column_index, column in enumerate(data["columns"])
        )
        return cls(
            name=str(contract.get("name", "schema_contract")),
            version=str(contract.get("version", "0.0.0")),
            layer=str(contract.get("layer", "silver")),
            columns=columns,
            enforcement=_parse_enforcement(data.get("enforcement", {})),
            raw=data,
        )

    def to_column_specs(self) -> list[ColumnSpec]:
        """Convert this schema contract into enforcer column specs."""
        from aetheriaforge.schema.enforcer import ColumnSpec

        return [
            ColumnSpec(name=column.name, dtype=column.dtype, nullable=column.nullable)
            for column in self.columns
        ]
