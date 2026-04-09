"""Forge engine: coherence-scored transformation with evidence writing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from aetheriaforge.config.contract import ForgeContract
from aetheriaforge.evidence.writer import EvidenceWriter
from aetheriaforge.forge.entropy import shannon_coherence_score
from aetheriaforge.forge.transformer import transform_dataframe
from aetheriaforge.schema.contract import SchemaContract


@dataclass
class ForgeResult:
    """Outcome of a single forge operation."""

    dataset_name: str
    coherence_score: float
    verdict: str
    threshold: float
    records_in: int
    records_out: int
    forged_at: str
    columns_in: list[str] = field(default_factory=list)
    columns_out: list[str] = field(default_factory=list)
    failure_reason: str | None = None
    evidence_path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return the result as a dictionary with an ``event`` key."""
        return {
            "event": "forge_result",
            "dataset_name": self.dataset_name,
            "coherence_score": self.coherence_score,
            "verdict": self.verdict,
            "threshold": self.threshold,
            "records_in": self.records_in,
            "records_out": self.records_out,
            "forged_at": self.forged_at,
            "columns_in": self.columns_in,
            "columns_out": self.columns_out,
            "failure_reason": self.failure_reason,
            "evidence_path": self.evidence_path,
        }


class ForgeEngine:
    """Coherence-scored transformation engine.

    Transforms a Bronze DataFrame into a target-shaped DataFrame from a schema
    contract, evaluates information preservation using Shannon entropy scoring,
    applies threshold verdicts, and optionally writes evidence artifacts.
    """

    WARN_TOLERANCE: float = 0.05

    def __init__(
        self,
        contract: ForgeContract,
        evidence_writer: EvidenceWriter | None = None,
    ) -> None:
        self.contract = contract
        self.evidence_writer = evidence_writer

    def forge(
        self,
        source: pd.DataFrame,
        forged: pd.DataFrame,
        target_layer: str = "silver",
    ) -> ForgeResult:
        """Score a transformation and return a :class:`ForgeResult`."""
        threshold = self.contract.threshold_for_layer(target_layer)
        score = shannon_coherence_score(source, forged)
        now_utc = datetime.now(tz=timezone.utc).isoformat()

        verdict: str
        failure_reason: str | None = None

        if score >= threshold:
            verdict = "PASS"
        elif score >= threshold - self.WARN_TOLERANCE:
            verdict = "WARN"
            failure_reason = (
                f"Coherence score {score:.6f} is below {target_layer} threshold "
                f"{threshold} but within WARN tolerance {self.WARN_TOLERANCE}"
            )
        else:
            verdict = "FAIL"
            failure_reason = (
                f"Coherence score {score:.6f} is below {target_layer} threshold "
                f"{threshold}"
            )

        result = ForgeResult(
            dataset_name=self.contract.dataset_name,
            coherence_score=score,
            verdict=verdict,
            threshold=threshold,
            records_in=len(source),
            records_out=len(forged),
            forged_at=now_utc,
            columns_in=list(source.columns),
            columns_out=list(forged.columns),
            failure_reason=failure_reason,
        )

        if self.evidence_writer is not None:
            evidence_path = self.evidence_writer.write(result.as_dict())
            result.evidence_path = str(evidence_path)

        return result

    def transform(
        self,
        source: pd.DataFrame,
        schema_contract: SchemaContract,
    ) -> pd.DataFrame:
        """Transform *source* into the target shape declared by *schema_contract*."""
        return transform_dataframe(source, schema_contract)

    def transform_and_forge(
        self,
        source: pd.DataFrame,
        schema_contract: SchemaContract,
        target_layer: str = "silver",
    ) -> tuple[pd.DataFrame, ForgeResult]:
        """Transform *source* via the schema contract and score the outcome."""
        forged = self.transform(source, schema_contract)
        return forged, self.forge(source, forged, target_layer=target_layer)
