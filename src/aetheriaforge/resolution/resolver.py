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
    """Resolve entities across two sources using configurable matching rules.

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
        """Perform exact-match resolution."""
        primary_keys = list(self.policy.sources[0].key_columns)
        secondary_keys = list(self.policy.sources[1].key_columns)
        ambiguity_behavior = self.policy.matching.ambiguity_behavior

        # Left join primary onto secondary
        merged = primary_df.merge(
            secondary_df,
            left_on=primary_keys,
            right_on=secondary_keys,
            how="left",
            indicator=True,
            suffixes=("", "_secondary"),
        )

        resolved_rows: list[dict[str, Any]] = []
        unresolved_rows: list[dict[str, Any]] = []
        decisions: list[MatchDecision] = []
        ambiguous_count = 0

        # Iterate by primary row index
        for p_idx in range(len(primary_df)):
            p_row = primary_df.iloc[p_idx]
            p_key_values = {k: p_row[k] for k in primary_keys}

            # Find matching rows in the merged result
            mask = pd.Series(True, index=merged.index)
            for pk in primary_keys:
                mask = mask & (merged[pk] == p_row[pk])
            matches = merged[mask & (merged["_merge"] == "both")]

            if len(matches) == 0:
                # NO_MATCH
                unresolved_rows.append(_series_to_dict(p_row))
                decisions.append(
                    MatchDecision(
                        primary_key_values=p_key_values,
                        secondary_key_values=None,
                        match_type="exact",
                        confidence=0.0,
                        verdict="NO_MATCH",
                    )
                )
            elif len(matches) == 1:
                # MATCHED
                matched_row = _series_to_dict(matches.iloc[0])
                matched_row.pop("_merge", None)
                resolved_rows.append(matched_row)

                s_key_values = {
                    k: matches.iloc[0].get(k, matches.iloc[0].get(k + "_secondary"))
                    for k in secondary_keys
                }
                decisions.append(
                    MatchDecision(
                        primary_key_values=p_key_values,
                        secondary_key_values=s_key_values,
                        match_type="exact",
                        confidence=1.0,
                        verdict="MATCHED",
                    )
                )
            else:
                # AMBIGUOUS
                ambiguous_count += 1

                if ambiguity_behavior == "fail":
                    msg = f"Ambiguous match for key {p_key_values}"
                    raise ValueError(msg)
                elif ambiguity_behavior == "best_match":
                    best_row = _series_to_dict(matches.iloc[0])
                    best_row.pop("_merge", None)
                    resolved_rows.append(best_row)

                    s_key_values = {
                        k: matches.iloc[0].get(
                            k, matches.iloc[0].get(k + "_secondary")
                        )
                        for k in secondary_keys
                    }
                    decisions.append(
                        MatchDecision(
                            primary_key_values=p_key_values,
                            secondary_key_values=s_key_values,
                            match_type="exact",
                            confidence=0.0,
                            verdict="AMBIGUOUS",
                        )
                    )
                else:
                    # skip (default)
                    unresolved_rows.append(_series_to_dict(p_row))
                    decisions.append(
                        MatchDecision(
                            primary_key_values=p_key_values,
                            secondary_key_values=None,
                            match_type="exact",
                            confidence=0.0,
                            verdict="AMBIGUOUS",
                        )
                    )

        resolved_df = pd.DataFrame(resolved_rows).reset_index(drop=True)
        unresolved_df = pd.DataFrame(unresolved_rows).reset_index(drop=True)

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
