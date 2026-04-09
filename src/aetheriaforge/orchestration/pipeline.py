"""Orchestration pipeline sequencing forge stages with evidence."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
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


def _schema_verdict(result: EnforcementResult) -> str:
    """Map schema enforcement output to a pipeline verdict."""
    if len(result.quarantined) == 0:
        return "PASS"
    if len(result.conformant) == 0:
        return "FAIL"
    return "WARN"


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
    schema_version: str = ""
    forged_df: pd.DataFrame | None = field(default=None, repr=False, compare=False)
    include_forged_df: bool = False

    def __post_init__(self) -> None:
        """Avoid retaining large DataFrames unless explicitly requested."""
        if self.forged_df is None:
            return
        if self.include_forged_df or self.execution_mode == "notebook":
            return
        self.forged_df = None

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
            "schema_version": self.schema_version,
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
    """Execute transformation, enforcement, scoring, resolution, and temporal stages."""

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
        forged_df: pd.DataFrame | None = None,
        schema_columns: list[ColumnSpec] | None = None,
        secondary_df: pd.DataFrame | None = None,
        resolution_policy: ResolutionPolicy | None = None,
        temporal_config: TemporalConfig | None = None,
        target_layer: str = "silver",
        execution_mode: str = "unverified",
        include_forged_df: bool = False,
    ) -> PipelineResult:
        """Execute the full forge pipeline and return a :class:`PipelineResult`."""
        if execution_mode not in EXECUTION_MODES:
            msg = (
                f"Invalid execution_mode {execution_mode!r}; must be one of "
                f"{sorted(EXECUTION_MODES)}"
            )
            raise ValueError(msg)

        schema_definition = self.contract.load_schema_contract()
        schema_version = (
            schema_definition.version if schema_definition is not None else ""
        )
        if schema_columns is None and schema_definition is not None:
            schema_columns = schema_definition.to_column_specs()

        if resolution_policy is None and self.contract.resolution_enabled:
            resolution_policy = self.contract.load_resolution_policy()
            if resolution_policy is None:
                msg = (
                    "Resolution is enabled in the forge contract but no "
                    "resolution policy is configured"
                )
                raise ValueError(msg)

        if self.contract.resolution_enabled and secondary_df is None:
            msg = (
                "Resolution is enabled in the forge contract but no secondary "
                "dataset was provided"
            )
            raise ValueError(msg)
        resolved_secondary_df = secondary_df

        if temporal_config is None and self.contract.temporal_enabled:
            temporal_config = self.contract.load_temporal_config()
            if temporal_config is None:
                msg = (
                    "Temporal reconciliation is enabled in the forge contract "
                    "but the required temporal configuration is missing"
                )
                raise ValueError(msg)

        verdicts: list[str] = []
        enforcement_result: EnforcementResult | None = None
        resolution_result: ResolutionResult | None = None
        temporal_result: TemporalResult | None = None

        engine = ForgeEngine(self.contract, evidence_writer=self.evidence_writer)
        transformed_df = forged_df
        if transformed_df is None:
            if schema_definition is None:
                msg = (
                    "No forged_df was supplied and the forge contract does not "
                    "reference a schema contract for transformation"
                )
                raise ValueError(msg)
            transformed_df = engine.transform(source_df, schema_definition)
        else:
            transformed_df = transformed_df.copy()

        working_forged = transformed_df

        effective_schema_config = self.contract.schema_contract
        if schema_definition is not None and "enforcement" in schema_definition.raw:
            effective_schema_config = replace(
                effective_schema_config,
                coerce_types=schema_definition.enforcement.type_coercion,
                unknown_columns=schema_definition.enforcement.unknown_columns,
                null_violation=schema_definition.enforcement.null_violation,
            )

        if schema_columns is not None and effective_schema_config.enforce:
            enforcer = SchemaEnforcer(schema_columns, effective_schema_config)
            enforcement_result = enforcer.enforce(working_forged)
            verdicts.append(_schema_verdict(enforcement_result))
            working_forged = enforcement_result.conformant

        if resolution_policy is not None:
            if resolved_secondary_df is None:
                msg = "Resolution policy was supplied without a secondary dataset"
                raise ValueError(msg)
            resolver = EntityResolver(
                resolution_policy,
                evidence_writer=self.evidence_writer,
            )
            resolution_result = resolver.resolve(working_forged, resolved_secondary_df)
            if resolution_result.ambiguous_count > 0:
                verdicts.append("WARN")
            working_forged = pd.concat(
                [resolution_result.resolved, resolution_result.unresolved],
                ignore_index=True,
                sort=False,
            )

        if temporal_config is not None:
            reconciler = TemporalReconciler(
                temporal_config,
                evidence_writer=self.evidence_writer,
            )
            temporal_result = reconciler.reconcile(working_forged)
            if temporal_result.conflict_count > 0:
                verdicts.append("WARN")
            working_forged = temporal_result.reconciled

        forge_result = engine.forge(source_df, working_forged, target_layer)
        verdicts.append(forge_result.verdict)

        pipeline_verdict = _worst_verdict(*verdicts) if verdicts else "PASS"
        now_utc = datetime.now(tz=timezone.utc).isoformat()

        src = self.contract
        source_loc = ".".join(
            p for p in (src.source_catalog, src.source_schema, src.source_table) if p
        ) or src.source_path
        target_loc = ".".join(
            p for p in (src.target_catalog, src.target_schema, src.target_table) if p
        ) or src.target_path

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
            schema_version=schema_version,
            forged_df=working_forged,
            include_forged_df=include_forged_df,
        )

        if self.evidence_writer is not None:
            evidence_path = self.evidence_writer.write(result.as_dict())
            result.evidence_path = str(evidence_path)

        if self.event_channel is not None:
            from aetheriaforge.integration.events import TransformationEvent

            event = TransformationEvent.from_pipeline_result(result, self.contract)
            self.event_channel.emit(event)

        return result
