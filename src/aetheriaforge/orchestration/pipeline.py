"""Orchestration pipeline sequencing forge stages with evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import pandas as pd

from aetheriaforge.config.contract import ForgeContract
from aetheriaforge.evidence.writer import EvidenceWriter
from aetheriaforge.forge.engine import ForgeEngine, ForgeResult

if TYPE_CHECKING:
    from aetheriaforge.integration.events import EventChannel
from aetheriaforge.resolution.policy import ResolutionPolicy
from aetheriaforge.resolution.resolver import EntityResolver, ResolutionResult
from aetheriaforge.schema.enforcer import (
    ColumnSpec,
    EnforcementResult,
    SchemaEnforcer,
)
from aetheriaforge.temporal.reconciler import (
    TemporalConfig,
    TemporalReconciler,
    TemporalResult,
)

_VERDICT_RANK: dict[str, int] = {"FAIL": 2, "WARN": 1, "PASS": 0}


def _worst_verdict(*verdicts: str) -> str:
    """Return the most severe verdict from the given set."""
    return max(verdicts, key=lambda v: _VERDICT_RANK.get(v, 0))


def _df_summary(df: pd.DataFrame) -> dict[str, int]:
    """Return a JSON-safe summary of a DataFrame's shape."""
    return {"rows": len(df), "columns": len(df.columns)}


EXECUTION_MODES = frozenset({"demo", "notebook", "contract_backed", "unverified"})


@dataclass
class PipelineResult:
    """Outcome of a full forge pipeline run."""

    dataset_name: str
    pipeline_verdict: str
    run_at: str
    forge_result: ForgeResult
    enforcement_result: EnforcementResult | None = None
    resolution_result: ResolutionResult | None = None
    temporal_result: TemporalResult | None = None
    evidence_path: str | None = None
    execution_mode: str = "unverified"
    source_location: str = ""
    target_location: str = ""
    contract_version: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Return the result as a dictionary with an ``event`` key."""
        result: dict[str, Any] = {
            "event": "pipeline_result",
            "dataset_name": self.dataset_name,
            "pipeline_verdict": self.pipeline_verdict,
            "run_at": self.run_at,
            "execution_mode": self.execution_mode,
            "source_location": self.source_location,
            "target_location": self.target_location,
            "contract_version": self.contract_version,
            "forge_result": self.forge_result.as_dict(),
            "evidence_path": self.evidence_path,
        }

        if self.enforcement_result is not None:
            result["enforcement_result"] = {
                "conformant": _df_summary(self.enforcement_result.conformant),
                "quarantined": _df_summary(self.enforcement_result.quarantined),
                "coercions_applied": self.enforcement_result.coercions_applied,
                "rejection_reasons": self.enforcement_result.rejection_reasons,
            }

        if self.resolution_result is not None:
            res = self.resolution_result.as_dict()
            res["resolved"] = _df_summary(self.resolution_result.resolved)
            res["unresolved"] = _df_summary(self.resolution_result.unresolved)
            result["resolution_result"] = res

        if self.temporal_result is not None:
            temp = self.temporal_result.as_dict()
            temp["reconciled"] = _df_summary(self.temporal_result.reconciled)
            result["temporal_result"] = temp

        return result


class ForgePipeline:
    """Sequences schema enforcement, forge scoring, resolution, and temporal reconciliation."""

    def __init__(
        self,
        contract: ForgeContract,
        evidence_writer: EvidenceWriter | None = None,
        event_channel: EventChannel | None = None,
    ) -> None:
        self.contract = contract
        self.evidence_writer = evidence_writer
        self.event_channel = event_channel

    def run(
        self,
        source_df: pd.DataFrame,
        forged_df: pd.DataFrame,
        schema_columns: list[ColumnSpec] | None = None,
        secondary_df: pd.DataFrame | None = None,
        resolution_policy: ResolutionPolicy | None = None,
        temporal_config: TemporalConfig | None = None,
        target_layer: str = "silver",
        execution_mode: str = "unverified",
    ) -> PipelineResult:
        """Execute the full forge pipeline and return a :class:`PipelineResult`.

        Stages execute in order: schema enforcement, forge scoring, entity
        resolution, temporal reconciliation.  Each stage is optional and
        controlled by the provided arguments.

        *execution_mode* is recorded in the evidence artifact to distinguish
        demo, notebook, contract-backed, and unverified runs.
        """
        if execution_mode not in EXECUTION_MODES:
            msg = f"Invalid execution_mode {execution_mode!r}; must be one of {sorted(EXECUTION_MODES)}"
            raise ValueError(msg)
        verdicts: list[str] = []
        enforcement_result: EnforcementResult | None = None
        resolution_result: ResolutionResult | None = None
        temporal_result: TemporalResult | None = None

        working_source = source_df

        # --- Stage 1: Schema enforcement ---
        if schema_columns is not None:
            enforcer = SchemaEnforcer(schema_columns, self.contract.schema_contract)
            enforcement_result = enforcer.enforce(source_df)
            if len(enforcement_result.quarantined) > 0:
                verdicts.append("WARN")
            else:
                verdicts.append("PASS")
            working_source = enforcement_result.conformant

        # --- Stage 2: Forge scoring ---
        engine = ForgeEngine(self.contract, evidence_writer=None)
        forge_result = engine.forge(working_source, forged_df, target_layer)
        verdicts.append(forge_result.verdict)

        # --- Stage 3: Entity resolution ---
        if resolution_policy is not None and secondary_df is not None:
            resolver = EntityResolver(resolution_policy, evidence_writer=None)
            resolution_result = resolver.resolve(forged_df, secondary_df)

        # --- Stage 4: Temporal reconciliation ---
        if temporal_config is not None:
            working_df: pd.DataFrame
            if resolution_result is not None:
                working_df = resolution_result.resolved
            else:
                working_df = forged_df
            reconciler = TemporalReconciler(temporal_config, evidence_writer=None)
            temporal_result = reconciler.reconcile(working_df)

        # --- Compute pipeline verdict ---
        pipeline_verdict = _worst_verdict(*verdicts) if verdicts else "PASS"
        now_utc = datetime.now(tz=timezone.utc).isoformat()

        # Build provenance strings from the contract.
        src = self.contract
        source_loc = ".".join(
            p for p in (src.source_catalog, src.source_schema, src.source_table) if p
        )
        target_loc = ".".join(
            p for p in (src.target_catalog, src.target_schema, src.target_table) if p
        )

        result = PipelineResult(
            dataset_name=self.contract.dataset_name,
            pipeline_verdict=pipeline_verdict,
            run_at=now_utc,
            forge_result=forge_result,
            enforcement_result=enforcement_result,
            resolution_result=resolution_result,
            temporal_result=temporal_result,
            execution_mode=execution_mode,
            source_location=source_loc,
            target_location=target_loc,
            contract_version=self.contract.dataset_version,
        )

        if self.evidence_writer is not None:
            evidence_path = self.evidence_writer.write(result.as_dict())
            result.evidence_path = str(evidence_path)

        if self.event_channel is not None:
            from aetheriaforge.integration.events import TransformationEvent

            event = TransformationEvent.from_pipeline_result(result, self.contract)
            self.event_channel.emit(event)

        return result
