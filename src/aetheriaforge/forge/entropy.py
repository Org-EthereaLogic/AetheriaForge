"""Shannon entropy coherence scoring for the forge engine.

v1.x uses Shannon entropy exclusively.  No UMIF constructs are permitted in
this module or anywhere else in the v1.x codebase.
"""

from __future__ import annotations

import pandas as pd
from scipy.stats import entropy as scipy_entropy


def column_entropy(series: pd.Series) -> float:  # type: ignore[type-arg]
    """Compute the Shannon entropy (base-2) of a column's value distribution.

    Returns 0.0 for empty or constant columns.
    """
    if series.empty:
        return 0.0
    counts = series.value_counts(dropna=False)
    if len(counts) <= 1:
        return 0.0
    probabilities = counts / counts.sum()
    return float(scipy_entropy(probabilities, base=2))


def shannon_coherence_score(source: pd.DataFrame, forged: pd.DataFrame) -> float:
    """Compute the information-preservation ratio between *source* and *forged*.

    Score semantics:
    - 1.0 = perfect preservation (no information lost)
    - 0.0 = total information loss

    Columns present in *forged* but absent from *source* are ignored (they do
    not count as loss).  Columns present in *source* but absent from *forged*
    contribute 0 preservation.
    """
    source_entropies: dict[str, float] = {}
    for col in source.columns:
        source_entropies[col] = column_entropy(source[col])

    total_source_entropy = sum(source_entropies.values())

    if total_source_entropy == 0.0:
        return 1.0

    preserved_entropy = 0.0
    for col in source.columns:
        if col in forged.columns:
            preserved_entropy += min(column_entropy(forged[col]), source_entropies[col])

    score = preserved_entropy / total_source_entropy
    score = max(0.0, min(1.0, score))
    return round(score, 6)
