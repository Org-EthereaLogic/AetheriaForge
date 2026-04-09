"""Schema enforcement against versioned contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from aetheriaforge.config.contract import SchemaContractConfig

_DTYPE_MAP: dict[str, str] = {
    "long": "int64",
    "integer": "int32",
    "double": "float64",
    "float": "float32",
    "string": "object",
    "boolean": "bool",
    "date": "object",
    "timestamp": "object",
}


def _normalize_dtype(raw: str) -> str:
    """Map contract types to pandas dtypes."""
    return _DTYPE_MAP.get(raw, raw)


@dataclass(frozen=True)
class ColumnSpec:
    """Expected column definition from a schema contract."""

    name: str
    dtype: str
    nullable: bool


@dataclass
class EnforcementResult:
    """Result of schema enforcement on a DataFrame."""

    conformant: pd.DataFrame
    quarantined: pd.DataFrame
    coercions_applied: list[str] = field(default_factory=list)
    rejection_reasons: list[str] = field(default_factory=list)


class SchemaEnforcer:
    """Validate, coerce, and quarantine records against a schema contract."""

    def __init__(self, columns: list[ColumnSpec], config: SchemaContractConfig) -> None:
        self.columns = [
            ColumnSpec(
                name=column.name,
                dtype=_normalize_dtype(column.dtype),
                nullable=column.nullable,
            )
            for column in columns
        ]
        self.config = config

    @classmethod
    def from_dict(
        cls,
        schema: list[dict[str, object]],
        config: SchemaContractConfig,
    ) -> SchemaEnforcer:
        """Build a :class:`SchemaEnforcer` from a list of column dictionaries."""
        specs: list[ColumnSpec] = []
        for col in schema:
            raw_type = str(col.get("type", "string"))
            mapped = _normalize_dtype(raw_type)
            specs.append(
                ColumnSpec(
                    name=str(col["name"]),
                    dtype=mapped,
                    nullable=bool(col.get("nullable", True)),
                )
            )
        return cls(specs, config)

    def enforce(self, df: pd.DataFrame) -> EnforcementResult:
        """Enforce the schema contract on *df* and return an :class:`EnforcementResult`."""
        coercions_applied: list[str] = []
        rejection_reasons: list[str] = []

        known_columns = {column.name for column in self.columns}
        extra_columns = sorted(column for column in df.columns if column not in known_columns)
        if extra_columns:
            reason = f"Unknown columns present: {extra_columns}"
            if self.config.unknown_columns == "reject":
                rejection_reasons.append(reason)
                return EnforcementResult(
                    conformant=pd.DataFrame(columns=[c.name for c in self.columns]),
                    quarantined=df.copy().reset_index(drop=True),
                    coercions_applied=coercions_applied,
                    rejection_reasons=rejection_reasons,
                )
            if self.config.unknown_columns == "quarantine":
                rejection_reasons.append(reason)
                df = df[[column for column in df.columns if column in known_columns]].copy()

        # --- Missing required columns ------------------------------------------
        required_columns = [c.name for c in self.columns if not c.nullable]
        missing = [c for c in required_columns if c not in df.columns]
        if missing:
            reason = f"Missing required columns: {missing}"
            rejection_reasons.append(reason)
            return EnforcementResult(
                conformant=pd.DataFrame(columns=df.columns),
                quarantined=df.copy().reset_index(drop=True),
                coercions_applied=coercions_applied,
                rejection_reasons=rejection_reasons,
            )

        # Defer copy until we actually need to mutate the DataFrame.
        working = df
        copied = False

        # --- Type coercion pass ------------------------------------------------
        if self.config.coerce_types:
            for spec in self.columns:
                if spec.name not in working.columns:
                    continue
                current_dtype = str(working[spec.name].dtype)
                if current_dtype != spec.dtype:
                    try:
                        if not copied:
                            working = df.copy()
                            copied = True
                        target_dtype: Any = spec.dtype
                        working[spec.name] = working[spec.name].astype(target_dtype)
                        coercions_applied.append(
                            f"Coerced column '{spec.name}' from {current_dtype} to {spec.dtype}"
                        )
                    except (ValueError, TypeError) as exc:
                        reason = f"Type coercion failed for column '{spec.name}': {exc}"
                        rejection_reasons.append(reason)
                        return EnforcementResult(
                            conformant=pd.DataFrame(columns=df.columns),
                            quarantined=df.copy().reset_index(drop=True),
                            coercions_applied=coercions_applied,
                            rejection_reasons=rejection_reasons,
                        )

        # --- Null violation pass -----------------------------------------------
        null_mask = pd.Series(False, index=working.index)
        for spec in self.columns:
            if spec.nullable:
                continue
            if spec.name not in working.columns:
                continue
            col_nulls = working[spec.name].isna()
            if col_nulls.any():
                n_nulls = int(col_nulls.sum())
                rejection_reasons.append(
                    f"Null violation in non-nullable column '{spec.name}': "
                    f"{n_nulls} row(s) quarantined"
                )
                if self.config.null_violation == "reject":
                    return EnforcementResult(
                        conformant=pd.DataFrame(columns=[c.name for c in self.columns]),
                        quarantined=working.copy().reset_index(drop=True),
                        coercions_applied=coercions_applied,
                        rejection_reasons=rejection_reasons,
                    )
                null_mask = null_mask | col_nulls

        conformant = working[~null_mask].reset_index(drop=True)
        quarantined = working[null_mask].reset_index(drop=True)

        if self.config.unknown_columns == "ignore":
            keep_columns = [column.name for column in self.columns if column.name in conformant.columns]
            conformant = conformant[keep_columns].reset_index(drop=True)
            quarantined = quarantined[keep_columns].reset_index(drop=True)

        return EnforcementResult(
            conformant=conformant,
            quarantined=quarantined,
            coercions_applied=coercions_applied,
            rejection_reasons=rejection_reasons,
        )
