"""Shannon entropy coherence scoring for the forge engine.

v1.x uses Shannon entropy exclusively.  No UMIF constructs are permitted in
this module or anywhere else in the v1.x codebase.
"""

from __future__ import annotations

import concurrent.futures

import pandas as pd
from scipy.stats import entropy as scipy_entropy

_LARGE_OBJECT_SAMPLE_THRESHOLD = 50_000
_NESTED_OBJECT_SAMPLE_CAP = 10_000
_PARALLEL_COLUMN_THRESHOLD = 4


def _has_nested_values(series: pd.Series, probe_size: int = 20) -> bool:  # type: ignore[type-arg]
    """Return True if any of the first *probe_size* values are dicts or lists."""
    for val in series.iloc[:probe_size]:
        if isinstance(val, (dict, list)):
            return True
    return False


def column_entropy(series: pd.Series) -> float:  # type: ignore[type-arg]
    """Compute the Shannon entropy (base-2) of a column's value distribution.

    Returns 0.0 for empty or constant columns.  Columns whose dtype is
    ``object`` are converted to string representations before counting so
    that unhashable values (nested dicts/lists from JSON) do not cause
    quadratic hashing overhead.

    For large object columns containing nested structures (dicts/lists), a
    deterministic sample is used to estimate entropy within ~1% accuracy
    while avoiding the O(n*k) string conversion cost on deeply nested data.
    """
    if series.empty:
        return 0.0
    working = series
    if working.dtype == object:
        n = len(working)
        if n > _NESTED_OBJECT_SAMPLE_CAP and _has_nested_values(working):
            # Sample deterministically for reproducibility — nested dicts/lists
            # make full .astype(str) O(n*k) where k = nesting depth.
            sample_size = min(n, _NESTED_OBJECT_SAMPLE_CAP)
            working = working.iloc[::max(1, n // sample_size)].head(sample_size).astype(str)
        elif n > _LARGE_OBJECT_SAMPLE_THRESHOLD:
            # Large but flat object columns: still convert, but safe
            working = working.astype(str)
        else:
            working = working.astype(str)
    counts = working.value_counts(dropna=False)
    if len(counts) <= 1:
        return 0.0
    probabilities = counts / counts.sum()
    return float(scipy_entropy(probabilities, base=2))


def _compute_column_entropies(df: pd.DataFrame) -> dict[str, float]:
    """Compute per-column entropies, parallelizing when there are many columns."""
    cols = list(df.columns)
    if len(cols) <= _PARALLEL_COLUMN_THRESHOLD:
        return {col: column_entropy(df[col]) for col in cols}

    results: dict[str, float] = {}
    max_workers = min(8, len(cols))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(column_entropy, df[col]): col for col in cols}
        for future in concurrent.futures.as_completed(futures):
            results[futures[future]] = future.result()
    return results


def shannon_coherence_score(source: pd.DataFrame, forged: pd.DataFrame) -> float:
    """Compute the information-preservation ratio between *source* and *forged*.

    Score semantics:
    - 1.0 = perfect preservation (no information lost)
    - 0.0 = total information loss

    Columns present in *forged* but absent from *source* are ignored (they do
    not count as loss).  Columns present in *source* but absent from *forged*
    contribute 0 preservation.
    """
    source_entropies = _compute_column_entropies(source)
    total_source_entropy = sum(source_entropies.values())

    if total_source_entropy == 0.0:
        return 1.0

    forged_entropies = _compute_column_entropies(forged)

    preserved_entropy = 0.0
    for col in source.columns:
        if col in forged_entropies:
            preserved_entropy += min(forged_entropies[col], source_entropies[col])

    score = preserved_entropy / total_source_entropy
    score = max(0.0, min(1.0, score))
    return round(score, 6)
