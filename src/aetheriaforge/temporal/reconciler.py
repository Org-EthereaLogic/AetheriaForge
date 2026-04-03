"""Temporal reconciliation engine for CDC, SCD Type 2, and batch sources."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from aetheriaforge.evidence.writer import EvidenceWriter


@dataclass(frozen=True)
class TemporalConfig:
    """Immutable configuration for temporal reconciliation."""

    timestamp_column: str
    merge_strategy: str
    conflict_behavior: str
    entity_key_columns: tuple[str, ...]


@dataclass
class TemporalConflict:
    """Record of a duplicate-timestamp conflict for an entity."""

    entity_key_values: dict[str, Any]
    conflicting_timestamps: list[Any] = field(default_factory=list)
    conflict_type: str = "DUPLICATE_TIMESTAMP"


@dataclass
class MergeDecision:
    """Record of a temporal merge decision for an entity."""

    entity_key_values: dict[str, Any]
    selected_timestamp: Any
    strategy_applied: str
    had_conflict: bool


@dataclass
class TemporalResult:
    """Outcome of a temporal reconciliation operation."""

    reconciled: pd.DataFrame
    conflicts: list[TemporalConflict] = field(default_factory=list)
    merge_decisions: list[MergeDecision] = field(default_factory=list)
    conflict_count: int = 0
    reconciled_count: int = 0
    reconciled_at: str = ""
    evidence_path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return the result as a dictionary with an ``event`` key."""
        return {
            "event": "temporal_result",
            "conflict_count": self.conflict_count,
            "reconciled_count": self.reconciled_count,
            "reconciled_at": self.reconciled_at,
            "evidence_path": self.evidence_path,
            "conflicts": [
                {
                    "entity_key_values": c.entity_key_values,
                    "conflicting_timestamps": [str(t) for t in c.conflicting_timestamps],
                    "conflict_type": c.conflict_type,
                }
                for c in self.conflicts
            ],
            "merge_decisions": [
                {
                    "entity_key_values": d.entity_key_values,
                    "selected_timestamp": str(d.selected_timestamp),
                    "strategy_applied": d.strategy_applied,
                    "had_conflict": d.had_conflict,
                }
                for d in self.merge_decisions
            ],
        }


def _series_to_dict(s: pd.Series) -> dict[str, Any]:  # type: ignore[type-arg]
    """Convert a pandas Series to a ``dict[str, Any]`` with string keys."""
    return {str(k): v for k, v in s.items()}


class TemporalReconciler:
    """Reconcile temporal records using configurable merge strategies.

    Only the ``latest_wins`` merge strategy is supported in v1.x.
    """

    def __init__(
        self,
        config: TemporalConfig,
        evidence_writer: EvidenceWriter | None = None,
    ) -> None:
        self.config = config
        self.evidence_writer = evidence_writer

    def reconcile(self, df: pd.DataFrame) -> TemporalResult:
        """Reconcile *df* by selecting one record per entity key group.

        Raises ``ValueError`` if required columns are missing or if a
        duplicate-timestamp conflict occurs with ``conflict_behavior='fail'``.
        Raises ``NotImplementedError`` for unsupported merge strategies.
        """
        ts_col = self.config.timestamp_column
        key_cols = list(self.config.entity_key_columns)

        # Validate columns exist
        missing = [c for c in [ts_col, *key_cols] if c not in df.columns]
        if missing:
            msg = f"Missing required columns in DataFrame: {missing}"
            raise ValueError(msg)

        if self.config.merge_strategy != "latest_wins":
            msg = (
                f"Only 'latest_wins' strategy is supported in v1.x "
                f"(got '{self.config.merge_strategy}')"
            )
            raise NotImplementedError(msg)

        return self._reconcile_latest_wins(df, ts_col, key_cols)

    def _reconcile_latest_wins(
        self,
        df: pd.DataFrame,
        ts_col: str,
        key_cols: list[str],
    ) -> TemporalResult:
        """Apply the latest_wins merge strategy."""
        conflicts: list[TemporalConflict] = []
        merge_decisions: list[MergeDecision] = []
        reconciled_rows: list[dict[str, Any]] = []

        grouped = df.groupby(key_cols, sort=False)

        for group_key, group_df in grouped:
            # Normalize group_key to a dict
            if isinstance(group_key, tuple):
                key_values = dict(zip(key_cols, group_key))
            else:
                key_values = {key_cols[0]: group_key}

            # Sort descending by timestamp (stable sort preserves row order for ties)
            sorted_group = group_df.sort_values(
                by=ts_col, ascending=False, kind="mergesort"
            )

            max_ts = sorted_group.iloc[0][ts_col]
            ties = sorted_group[sorted_group[ts_col] == max_ts]
            had_conflict = len(ties) > 1

            if had_conflict:
                conflict = TemporalConflict(
                    entity_key_values=key_values,
                    conflicting_timestamps=[max_ts] * len(ties),
                    conflict_type="DUPLICATE_TIMESTAMP",
                )
                conflicts.append(conflict)

                if self.config.conflict_behavior == "fail":
                    msg = f"Duplicate timestamp conflict for entity {key_values}"
                    raise ValueError(msg)

            # Select the first row after stable descending sort
            selected = sorted_group.iloc[0]
            reconciled_rows.append(_series_to_dict(selected))

            merge_decisions.append(
                MergeDecision(
                    entity_key_values=key_values,
                    selected_timestamp=selected[ts_col],
                    strategy_applied="latest_wins",
                    had_conflict=had_conflict,
                )
            )

        reconciled_df = pd.DataFrame(reconciled_rows).reset_index(drop=True)
        now_utc = datetime.now(tz=timezone.utc).isoformat()

        result = TemporalResult(
            reconciled=reconciled_df,
            conflicts=conflicts,
            merge_decisions=merge_decisions,
            conflict_count=len(conflicts),
            reconciled_count=len(reconciled_df),
            reconciled_at=now_utc,
        )

        if self.evidence_writer is not None:
            evidence_path = self.evidence_writer.write(result.as_dict())
            result.evidence_path = str(evidence_path)

        return result
