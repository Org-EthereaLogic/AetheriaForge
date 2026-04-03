"""Tests for schema enforcement against versioned contracts.

Traces: AF-SR-005, AF-FR-009
"""

from __future__ import annotations

import pandas as pd

from aetheriaforge.config import SchemaContractConfig
from aetheriaforge.schema import ColumnSpec, SchemaEnforcer


def _default_config(coerce: bool = True) -> SchemaContractConfig:
    return SchemaContractConfig(enforce=True, evolution="versioned", coerce_types=coerce)


def _simple_schema() -> list[ColumnSpec]:
    return [
        ColumnSpec(name="id", dtype="int64", nullable=False),
        ColumnSpec(name="name", dtype="object", nullable=False),
        ColumnSpec(name="amount", dtype="float64", nullable=True),
    ]


def test_conformant_records_pass_through() -> None:
    """All valid records pass through with an empty quarantine."""
    df = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["a", "b", "c"],
            "amount": [10.0, 20.0, 30.0],
        }
    )
    enforcer = SchemaEnforcer(_simple_schema(), _default_config())
    result = enforcer.enforce(df)

    assert len(result.conformant) == 3
    assert len(result.quarantined) == 0
    assert result.rejection_reasons == []


def test_missing_required_column_quarantines_all() -> None:
    """Dropping a required column quarantines every row."""
    df = pd.DataFrame(
        {
            "id": [1, 2],
            "amount": [10.0, 20.0],
        }
    )
    enforcer = SchemaEnforcer(_simple_schema(), _default_config())
    result = enforcer.enforce(df)

    assert len(result.conformant) == 0
    assert len(result.quarantined) == 2
    assert any("Missing required columns" in r for r in result.rejection_reasons)


def test_null_violation_quarantines_row() -> None:
    """A null in a non-nullable column quarantines only the offending rows."""
    df = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["a", None, "c"],
            "amount": [10.0, 20.0, 30.0],
        }
    )
    enforcer = SchemaEnforcer(_simple_schema(), _default_config())
    result = enforcer.enforce(df)

    assert len(result.conformant) == 2
    assert len(result.quarantined) == 1
    assert any("Null violation" in r for r in result.rejection_reasons)


def test_type_coercion_applied() -> None:
    """Integer column stored as string is coerced to int64."""
    df = pd.DataFrame(
        {
            "id": ["1", "2", "3"],
            "name": ["a", "b", "c"],
            "amount": [10.0, 20.0, 30.0],
        }
    )
    enforcer = SchemaEnforcer(_simple_schema(), _default_config())
    result = enforcer.enforce(df)

    assert len(result.coercions_applied) > 0
    assert str(result.conformant["id"].dtype) == "int64"


def test_coercion_failure_quarantines_all() -> None:
    """Non-coercible values quarantine all records."""
    df = pd.DataFrame(
        {
            "id": ["not_a_number", "still_not", "nope"],
            "name": ["a", "b", "c"],
            "amount": [10.0, 20.0, 30.0],
        }
    )
    enforcer = SchemaEnforcer(_simple_schema(), _default_config())
    result = enforcer.enforce(df)

    assert len(result.conformant) == 0
    assert len(result.quarantined) == 3
    assert any("coercion failed" in r.lower() for r in result.rejection_reasons)


def test_from_dict_builds_enforcer() -> None:
    """from_dict correctly maps schema dictionaries to ColumnSpec entries."""
    schema_list: list[dict[str, object]] = [
        {"name": "id", "type": "long", "nullable": False},
        {"name": "value", "type": "double", "nullable": True},
    ]
    enforcer = SchemaEnforcer.from_dict(schema_list, _default_config())

    assert len(enforcer.columns) == 2
    assert enforcer.columns[0].name == "id"
    assert enforcer.columns[0].dtype == "int64"
    assert enforcer.columns[1].name == "value"
    assert enforcer.columns[1].dtype == "float64"
