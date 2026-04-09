"""Direct tests for schema-contract transformation behavior."""

from __future__ import annotations

import pandas as pd
import pytest

from aetheriaforge.forge import TransformationError, transform_dataframe
from aetheriaforge.schema import SchemaContract


def _schema_contract(columns: list[dict[str, object]]) -> SchemaContract:
    return SchemaContract.from_dict(
        {
            "contract": {"name": "transform", "version": "1.0.0", "layer": "silver"},
            "columns": columns,
        }
    )


def test_transform_dataframe_supports_multiple_operations() -> None:
    """Transform steps cover string, numeric, concat, coalesce, default, and nullable cases."""
    source = pd.DataFrame(
        {
            "name": ["  Alice  ", "Bob"],
            "nickname": [None, "Bobby"],
            "last": ["Smith", "Jones"],
            "amount": [10.0, 20.0],
            "missing_fill": [None, "provided"],
        }
    )
    schema = _schema_contract(
        [
            {
                "name": "name_clean",
                "type": "string",
                "nullable": False,
                "source": "name",
                "transforms": [{"op": "strip"}, {"op": "lower"}],
            },
            {
                "name": "amount_calc",
                "type": "double",
                "nullable": False,
                "source": "amount",
                "transforms": [
                    {"op": "multiply", "value": 2},
                    {"op": "divide", "value": 4},
                    {"op": "add", "value": 1},
                    {"op": "subtract", "value": 0.5},
                    {"op": "round", "value": 1},
                ],
            },
            {
                "name": "filled",
                "type": "string",
                "nullable": True,
                "source": "missing_fill",
                "transforms": [{"op": "fillna", "value": "fallback"}],
            },
            {
                "name": "full_name",
                "type": "string",
                "nullable": False,
                "source": "name",
                "transforms": [
                    {"op": "strip"},
                    {"op": "concat", "sources": ["last"], "separator": "-"},
                ],
            },
            {
                "name": "preferred_name",
                "type": "string",
                "nullable": True,
                "source": "nickname",
                "transforms": [{"op": "coalesce", "sources": ["last"]}],
            },
            {
                "name": "defaulted",
                "type": "string",
                "nullable": False,
                "default": "standard",
            },
            {
                "name": "optional_blank",
                "type": "string",
                "nullable": True,
            },
        ]
    )

    transformed = transform_dataframe(source, schema)

    assert transformed["name_clean"].tolist() == ["alice", "bob"]
    assert transformed["amount_calc"].tolist() == [5.5, 10.5]
    assert transformed["filled"].tolist() == ["fallback", "provided"]
    assert transformed["full_name"].tolist() == ["Alice-Smith", "Bob-Jones"]
    assert transformed["preferred_name"].tolist() == ["Smith", "Bobby"]
    assert transformed["defaulted"].tolist() == ["standard", "standard"]
    assert transformed["optional_blank"].isna().all()


@pytest.mark.parametrize(
    ("columns", "message"),
    [
        (
            [
                {
                    "name": "amount",
                    "type": "double",
                    "nullable": False,
                    "source": "amount",
                    "transforms": [{"op": "multiply"}],
                }
            ],
            "requires a value",
        ),
        (
            [
                {
                    "name": "amount",
                    "type": "double",
                    "nullable": False,
                    "source": "amount",
                    "transforms": [{"op": "multiply", "value": "bad"}],
                }
            ],
            "requires a numeric value",
        ),
        (
            [
                {
                    "name": "amount",
                    "type": "double",
                    "nullable": False,
                    "source": "amount",
                    "transforms": [{"op": "round", "value": "bad"}],
                }
            ],
            "requires an integer value",
        ),
        (
            [
                {
                    "name": "amount",
                    "type": "double",
                    "nullable": False,
                    "source": "amount",
                    "transforms": [{"op": "round"}],
                }
            ],
            "requires a value",
        ),
        (
            [
                {
                    "name": "amount",
                    "type": "double",
                    "nullable": False,
                    "source": "amount",
                    "transforms": [{"op": "divide", "value": 0}],
                }
            ],
            "cannot use zero",
        ),
    ],
)
def test_transform_dataframe_validates_transform_values(
    columns: list[dict[str, object]],
    message: str,
) -> None:
    """Missing or invalid transform parameters raise explicit errors."""
    source = pd.DataFrame({"amount": [10.0]})
    schema = _schema_contract(columns)

    with pytest.raises(TransformationError, match=message):
        transform_dataframe(source, schema)


def test_transform_dataframe_rejects_non_numeric_operations_on_text() -> None:
    """Numeric transform ops fail on non-numeric source data."""
    source = pd.DataFrame({"amount": ["bad"]})
    schema = _schema_contract(
        [
            {
                "name": "amount",
                "type": "double",
                "nullable": False,
                "source": "amount",
                "transforms": [{"op": "add", "value": 1}],
            }
        ]
    )

    with pytest.raises(TransformationError, match="requires numeric data"):
        transform_dataframe(source, schema)


def test_transform_dataframe_rejects_missing_concat_source() -> None:
    """Concat fallbacks still require declared source columns to exist."""
    source = pd.DataFrame({"name": ["Alice"]})
    schema = _schema_contract(
        [
            {
                "name": "full_name",
                "type": "string",
                "nullable": False,
                "source": "name",
                "transforms": [{"op": "concat", "sources": ["missing"]}],
            }
        ]
    )

    with pytest.raises(TransformationError, match="Missing required source column"):
        transform_dataframe(source, schema)


def test_transform_dataframe_rejects_unknown_operations() -> None:
    """Unsupported transform operations fail closed."""
    source = pd.DataFrame({"name": ["Alice"]})
    schema = _schema_contract(
        [
            {
                "name": "name",
                "type": "string",
                "nullable": False,
                "transforms": [{"op": "mystery"}],
            }
        ]
    )

    with pytest.raises(TransformationError, match="Unsupported transform op"):
        transform_dataframe(source, schema)


def test_transform_dataframe_requires_columns() -> None:
    """An empty schema contract is not valid for transformation."""
    schema = _schema_contract([])

    with pytest.raises(TransformationError, match="must declare at least one"):
        transform_dataframe(pd.DataFrame({"id": [1]}), schema)
