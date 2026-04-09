"""Cross-source entity resolution engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from aetheriaforge.evidence.writer import EvidenceWriter
from aetheriaforge.resolution.policy import ResolutionPolicy


@dataclass
class MatchDecision:
    """Record of a single match decision during entity resolution."""

    primary_key_values: dict[str, Any]
    secondary_key_values: dict[str, Any] | None
    match_type: str
    confidence: float
    verdict: str


@dataclass
class ResolutionResult:
    """Outcome of a cross-source entity resolution operation."""

    resolved: pd.DataFrame
    unresolved: pd.DataFrame
    decisions: list[MatchDecision] = field(default_factory=list)
    resolved_count: int = 0
    unresolved_count: int = 0
    ambiguous_count: int = 0
    resolved_at: str = ""
    evidence_path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return the result as a dictionary with an ``event`` key."""
        return {
            "event": "resolution_result",
            "resolved_count": self.resolved_count,
            "unresolved_count": self.unresolved_count,
            "ambiguous_count": self.ambiguous_count,
            "resolved_at": self.resolved_at,
            "evidence_path": self.evidence_path,
            "decisions": [
                {
                    "primary_key_values": d.primary_key_values,
                    "secondary_key_values": d.secondary_key_values,
                    "match_type": d.match_type,
                    "confidence": d.confidence,
                    "verdict": d.verdict,
                }
                for d in self.decisions
            ],
        }


def _series_to_dict(s: pd.Series) -> dict[str, Any]:  # type: ignore[type-arg]
    """Convert a pandas Series to a ``dict[str, Any]`` with string keys."""
    return {str(k): v for k, v in s.items()}


class EntityResolver:
    """Resolve entities across two sources using configured exact key rules.

    Only the ``exact`` matching strategy is supported in v1.x.
    """

    def __init__(
        self,
        policy: ResolutionPolicy,
        evidence_writer: EvidenceWriter | None = None,
    ) -> None:
        self.policy = policy
        self.evidence_writer = evidence_writer

    def resolve(
        self, primary_df: pd.DataFrame, secondary_df: pd.DataFrame
    ) -> ResolutionResult:
        """Resolve entities between *primary_df* and *secondary_df*.

        Raises ``ValueError`` if fewer than two sources are defined in the
        policy, and ``NotImplementedError`` for non-exact strategies.
        """
        if len(self.policy.sources) < 2:
            msg = "Resolution requires at least two sources"
            raise ValueError(msg)

        strategy = self.policy.matching.strategy
        if strategy != "exact":
            msg = f"Only 'exact' strategy is supported in v1.x (got '{strategy}')"
            raise NotImplementedError(msg)

        return self._resolve_exact(primary_df, secondary_df)

    def _resolve_exact(
        self, primary_df: pd.DataFrame, secondary_df: pd.DataFrame
    ) -> ResolutionResult:
        """Perform exact-match resolution.

        Uses vectorized pandas merge and groupby operations instead of
        per-row iteration to keep resolution O(n log n) rather than O(n^2).
        """
        primary_keys = list(self.policy.sources[0].key_columns)
        secondary_keys = list(self.policy.sources[1].key_columns)
        ambiguity_behavior = self.policy.matching.ambiguity_behavior

        # Tag primary rows so we can trace them after merge.
        primary = primary_df.copy()
        primary["_af_pidx"] = range(len(primary))

        # Left join primary onto secondary
        merged = primary.merge(
            secondary_df,
            left_on=primary_keys,
            right_on=secondary_keys,
            how="left",
            indicator=True,
            suffixes=("", "_secondary"),
        )

        # Count matches per primary row
        match_counts = (
            merged[merged["_merge"] == "both"]
            .groupby("_af_pidx", sort=False)
            .size()
            .reset_index(name="_match_count")
        )

        # Classify each primary row
        primary = primary.merge(match_counts, on="_af_pidx", how="left")
        primary["_match_count"] = primary["_match_count"].fillna(0).astype(int)

        no_match_mask = primary["_match_count"] == 0
        single_match_mask = primary["_match_count"] == 1
        ambiguous_mask = primary["_match_count"] > 1

        # --- NO_MATCH rows ---
        unresolved_indices = primary.index[no_match_mask | (ambiguous_mask & (ambiguity_behavior == "skip"))]

        # --- Build resolved rows ---
        # For single matches, take the merged row directly
        single_pidxs = set(primary.loc[single_match_mask, "_af_pidx"])
        matched_merged = merged[
            (merged["_merge"] == "both") & merged["_af_pidx"].isin(single_pidxs)
        ].copy()

        ambiguous_pidxs = set(primary.loc[ambiguous_mask, "_af_pidx"])
        ambiguous_count = len(ambiguous_pidxs)

        if ambiguity_behavior == "fail" and ambiguous_count > 0:
            first_amb = primary.loc[ambiguous_mask].iloc[0]
            p_key_values = {k: first_amb[k] for k in primary_keys}
            msg = f"Ambiguous match for key {p_key_values}"
            raise ValueError(msg)

        if ambiguity_behavior == "best_match" and ambiguous_pidxs:
            # Take first match per ambiguous primary row
            best_matches = (
                merged[(merged["_merge"] == "both") & merged["_af_pidx"].isin(ambiguous_pidxs)]
                .groupby("_af_pidx", sort=False)
                .first()
                .reset_index()
            )
            matched_merged = pd.concat([matched_merged, best_matches], ignore_index=True)
        elif ambiguity_behavior == "skip" and ambiguous_pidxs:
            pass  # already added to unresolved above

        # Drop internal columns
        drop_cols = [c for c in ["_merge", "_af_pidx", "_match_count"] if c in matched_merged.columns]
        resolved_df = matched_merged.drop(columns=drop_cols).reset_index(drop=True)

        # Build unresolved from primary
        unresolved_df = primary_df.iloc[unresolved_indices].reset_index(drop=True)

        # --- Build decisions (summary-level, not per-row for large datasets) ---
        decisions: list[MatchDecision] = []
        sample_limit = 1000
        include_rejected = (
            self.policy.record_all_decisions and self.policy.include_rejected_matches
        )

        if include_rejected:
            no_match_primary = primary_df.iloc[primary.index[no_match_mask]]
            for _, row in no_match_primary.head(sample_limit).iterrows():
                decisions.append(
                    MatchDecision(
                        primary_key_values={k: row[k] for k in primary_keys},
                        secondary_key_values=None,
                        match_type="exact",
                        confidence=0.0,
                        verdict="NO_MATCH",
                    )
                )

        single_primary = primary_df.iloc[primary.index[single_match_mask]]
        for _, row in single_primary.head(sample_limit).iterrows():
            decisions.append(
                MatchDecision(
                    primary_key_values={k: row[k] for k in primary_keys},
                    secondary_key_values=None,
                    match_type="exact",
                    confidence=1.0,
                    verdict="MATCHED",
                )
            )

        if include_rejected:
            amb_primary = primary_df.iloc[primary.index[ambiguous_mask]]
            for _, row in amb_primary.head(sample_limit).iterrows():
                decisions.append(
                    MatchDecision(
                        primary_key_values={k: row[k] for k in primary_keys},
                        secondary_key_values=None,
                        match_type="exact",
                        confidence=0.0,
                        verdict="AMBIGUOUS",
                    )
                )

        now_utc = datetime.now(tz=timezone.utc).isoformat()

        result = ResolutionResult(
            resolved=resolved_df,
            unresolved=unresolved_df,
            decisions=decisions,
            resolved_count=len(resolved_df),
            unresolved_count=len(unresolved_df),
            ambiguous_count=ambiguous_count,
            resolved_at=now_utc,
        )

        if self.evidence_writer is not None:
            evidence_path = self.evidence_writer.write(result.as_dict())
            result.evidence_path = str(evidence_path)

        return result
