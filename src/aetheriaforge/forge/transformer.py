"""Contract-driven DataFrame transformation utilities."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

import pandas as pd

from aetheriaforge.schema.contract import (
    SchemaColumn,
    SchemaContract,
    TransformStep,
)


class TransformationError(ValueError):
    """Raised when a contract-driven transformation cannot be completed."""


def _require_float_value(step: TransformStep, *, column_name: str) -> float:
    """Return a numeric transform value or raise a transformation error."""
    if step.value is None:
        msg = f"Transformation '{step.op}' requires a value for '{column_name}'"
        raise TransformationError(msg)
    try:
        return float(step.value)
    except (TypeError, ValueError) as exc:
        msg = f"Transformation '{step.op}' requires a numeric value for '{column_name}'"
        raise TransformationError(msg) from exc


def _require_int_value(step: TransformStep, *, column_name: str) -> int:
    """Return an integer transform value or raise a transformation error."""
    if step.value is None:
        msg = f"Transformation '{step.op}' requires a value for '{column_name}'"
        raise TransformationError(msg)
    try:
        return int(step.value)
    except (TypeError, ValueError) as exc:
        msg = f"Transformation '{step.op}' requires an integer value for '{column_name}'"
        raise TransformationError(msg) from exc


def _null_series(length: int, index: pd.Index) -> pd.Series:  # type: ignore[type-arg]
    """Create a nullable object-typed Series of the requested length."""
    return pd.Series([None] * length, index=index, dtype="object")


def _numeric_series(series: pd.Series, *, op: str, column_name: str) -> pd.Series:  # type: ignore[type-arg]
    """Convert a series to numeric values or raise a transformation error."""
    converted = pd.to_numeric(series, errors="coerce")
    if converted.isna().any() and not series.isna().equals(converted.isna()):
        msg = (
            f"Transformation '{op}' requires numeric data for column '{column_name}'"
        )
        raise TransformationError(msg)
    return converted


def _resolve_source_series(
    source_df: pd.DataFrame,
    source_name: str,
    *,
    column_name: str,
) -> pd.Series:  # type: ignore[type-arg]
    """Return one source column or raise a transformation error."""
    if source_name not in source_df.columns:
        msg = f"Missing required source column '{source_name}' for '{column_name}'"
        raise TransformationError(msg)
    return source_df[source_name].copy()


def _build_initial_series(
    source_df: pd.DataFrame,
    column: SchemaColumn,
) -> pd.Series:  # type: ignore[type-arg]
    """Construct the initial series for one target column."""
    source_name = column.source or column.name
    if source_name in source_df.columns:
        return source_df[source_name].copy()
    if column.has_default:
        return pd.Series(
            [column.default] * len(source_df),
            index=source_df.index,
            dtype="object",
        )
    if column.nullable:
        return _null_series(len(source_df), source_df.index)
    msg = f"Missing required source column '{source_name}' for '{column.name}'"
    raise TransformationError(msg)


def _op_strip(
    series: pd.Series,  # type: ignore[type-arg]
    source_df: pd.DataFrame,
    column: SchemaColumn,
    step: TransformStep,
) -> pd.Series:  # type: ignore[type-arg]
    del source_df, column, step
    return series.astype("string").str.strip()


def _op_lower(
    series: pd.Series,  # type: ignore[type-arg]
    source_df: pd.DataFrame,
    column: SchemaColumn,
    step: TransformStep,
) -> pd.Series:  # type: ignore[type-arg]
    del source_df, column, step
    return series.astype("string").str.lower()


def _op_upper(
    series: pd.Series,  # type: ignore[type-arg]
    source_df: pd.DataFrame,
    column: SchemaColumn,
    step: TransformStep,
) -> pd.Series:  # type: ignore[type-arg]
    del source_df, column, step
    return series.astype("string").str.upper()


def _op_fillna(
    series: pd.Series,  # type: ignore[type-arg]
    source_df: pd.DataFrame,
    column: SchemaColumn,
    step: TransformStep,
) -> pd.Series:  # type: ignore[type-arg]
    del source_df, column
    return series.fillna(step.value)


def _op_multiply(
    series: pd.Series,  # type: ignore[type-arg]
    source_df: pd.DataFrame,
    column: SchemaColumn,
    step: TransformStep,
) -> pd.Series:  # type: ignore[type-arg]
    del source_df
    numeric = _numeric_series(series, op="multiply", column_name=column.name)
    factor = _require_float_value(step, column_name=column.name)
    return cast(pd.Series, numeric * factor)


def _op_divide(
    series: pd.Series,  # type: ignore[type-arg]
    source_df: pd.DataFrame,
    column: SchemaColumn,
    step: TransformStep,
) -> pd.Series:  # type: ignore[type-arg]
    del source_df
    divisor = _require_float_value(step, column_name=column.name)
    if divisor == 0:
        msg = f"Transformation 'divide' cannot use zero for '{column.name}'"
        raise TransformationError(msg)
    numeric = _numeric_series(series, op="divide", column_name=column.name)
    return cast(pd.Series, numeric / divisor)


def _op_add(
    series: pd.Series,  # type: ignore[type-arg]
    source_df: pd.DataFrame,
    column: SchemaColumn,
    step: TransformStep,
) -> pd.Series:  # type: ignore[type-arg]
    del source_df
    numeric = _numeric_series(series, op="add", column_name=column.name)
    addend = _require_float_value(step, column_name=column.name)
    return cast(pd.Series, numeric + addend)


def _op_subtract(
    series: pd.Series,  # type: ignore[type-arg]
    source_df: pd.DataFrame,
    column: SchemaColumn,
    step: TransformStep,
) -> pd.Series:  # type: ignore[type-arg]
    del source_df
    numeric = _numeric_series(series, op="subtract", column_name=column.name)
    subtrahend = _require_float_value(step, column_name=column.name)
    return cast(pd.Series, numeric - subtrahend)


def _op_round(
    series: pd.Series,  # type: ignore[type-arg]
    source_df: pd.DataFrame,
    column: SchemaColumn,
    step: TransformStep,
) -> pd.Series:  # type: ignore[type-arg]
    del source_df
    numeric = _numeric_series(series, op="round", column_name=column.name)
    digits = _require_int_value(step, column_name=column.name)
    return cast(pd.Series, numeric.round(digits))


def _op_concat(
    series: pd.Series,  # type: ignore[type-arg]
    source_df: pd.DataFrame,
    column: SchemaColumn,
    step: TransformStep,
) -> pd.Series:  # type: ignore[type-arg]
    parts = [series.astype("string")]
    for source_name in step.sources:
        parts.append(
            _resolve_source_series(
                source_df,
                source_name,
                column_name=column.name,
            ).astype("string")
        )
    combined = parts[0].fillna("")
    for extra in parts[1:]:
        combined = combined + step.separator + extra.fillna("")
    return combined.str.strip()


def _op_coalesce(
    series: pd.Series,  # type: ignore[type-arg]
    source_df: pd.DataFrame,
    column: SchemaColumn,
    step: TransformStep,
) -> pd.Series:  # type: ignore[type-arg]
    result = series.copy()
    for source_name in step.sources:
        fallback = _resolve_source_series(
            source_df,
            source_name,
            column_name=column.name,
        )
        result = result.where(result.notna(), fallback)
    return result


_TransformOp = Callable[
    [
        "pd.Series",  # type: ignore[type-arg]
        pd.DataFrame,
        SchemaColumn,
        TransformStep,
    ],
    "pd.Series",  # type: ignore[type-arg]
]


_TRANSFORM_OPS: dict[str, _TransformOp] = {
    "strip": _op_strip,
    "lower": _op_lower,
    "upper": _op_upper,
    "fillna": _op_fillna,
    "multiply": _op_multiply,
    "divide": _op_divide,
    "add": _op_add,
    "subtract": _op_subtract,
    "round": _op_round,
    "concat": _op_concat,
    "coalesce": _op_coalesce,
}


def _apply_transform(
    series: pd.Series,  # type: ignore[type-arg]
    source_df: pd.DataFrame,
    column: SchemaColumn,
    step: TransformStep,
) -> pd.Series:  # type: ignore[type-arg]
    """Apply one supported transform operation."""
    handler = _TRANSFORM_OPS.get(step.op)
    if handler is None:
        msg = f"Unsupported transform op '{step.op}' for column '{column.name}'"
        raise TransformationError(msg)
    return handler(series, source_df, column, step)


def transform_dataframe(
    source_df: pd.DataFrame,
    schema_contract: SchemaContract,
) -> pd.DataFrame:
    """Transform *source_df* into the target shape declared by *schema_contract*."""
    if not schema_contract.columns:
        msg = "Schema contract must declare at least one target column"
        raise TransformationError(msg)

    transformed: dict[str, pd.Series] = {}
    for column in schema_contract.columns:
        series = _build_initial_series(source_df, column)
        for step in column.transforms:
            series = _apply_transform(series, source_df, column, step)
        transformed[column.name] = series.reset_index(drop=True)

    return pd.DataFrame(transformed).reset_index(drop=True)
