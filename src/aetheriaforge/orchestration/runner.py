"""Multi-dataset forge runner — batch pipeline execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import pandas as pd

from aetheriaforge.config.registry import DatasetRegistry
from aetheriaforge.evidence.writer import EvidenceWriter
from aetheriaforge.orchestration.pipeline import ForgePipeline, PipelineResult

if TYPE_CHECKING:
    from aetheriaforge.integration.events import EventChannel
from aetheriaforge.resolution.policy import ResolutionPolicy
from aetheriaforge.schema.enforcer import ColumnSpec
from aetheriaforge.temporal.reconciler import TemporalConfig

_VERDICT_RANK: dict[str, int] = {"FAIL": 2, "WARN": 1, "PASS": 0}


@dataclass
class DatasetInput:
    """All data needed to run a forge pipeline for one dataset."""

    source_df: pd.DataFrame
    forged_df: pd.DataFrame | None = None
    schema_columns: list[ColumnSpec] | None = None
    secondary_df: pd.DataFrame | None = None
    resolution_policy: ResolutionPolicy | None = None
    temporal_config: TemporalConfig | None = None
    target_layer: str = "silver"
    execution_mode: str = "unverified"


@dataclass
class BatchResult:
    """Outcome of a multi-dataset forge run."""

    results: dict[str, PipelineResult] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)
    batch_verdict: str = "PASS"
    run_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary of the batch outcome."""
        return {
            "event": "batch_result",
            "batch_verdict": self.batch_verdict,
            "run_at": self.run_at,
            "dataset_count": len(self.results),
            "skipped": self.skipped,
            "datasets": {
                name: result.as_dict() for name, result in self.results.items()
            },
        }


class ForgeRunner:
    """Execute forge pipelines across multiple registered datasets."""

    def __init__(
        self,
        registry: DatasetRegistry,
        evidence_writer: EvidenceWriter | None = None,
        event_channel: EventChannel | None = None,
    ) -> None:
        self.registry = registry
        self.evidence_writer = evidence_writer
        self.event_channel = event_channel

    def run_one(self, name: str, dataset_input: DatasetInput) -> PipelineResult:
        """Run the forge pipeline for a single named dataset.

        Raises ``KeyError`` if *name* is not in the registry.
        """
        contract = self.registry.get(name)
        pipeline = ForgePipeline(
            contract,
            evidence_writer=self.evidence_writer,
            event_channel=self.event_channel,
        )
        return pipeline.run(
            source_df=dataset_input.source_df,
            forged_df=dataset_input.forged_df,
            schema_columns=dataset_input.schema_columns,
            secondary_df=dataset_input.secondary_df,
            resolution_policy=dataset_input.resolution_policy,
            temporal_config=dataset_input.temporal_config,
            target_layer=dataset_input.target_layer,
            execution_mode=dataset_input.execution_mode,
        )

    def run(self, inputs: dict[str, DatasetInput]) -> BatchResult:
        """Run forge pipelines for all datasets present in both the registry and *inputs*.

        Datasets in one but not the other are recorded in ``BatchResult.skipped``.
        """
        registered = set(self.registry.list_datasets())
        provided = set(inputs)
        processable = registered & provided
        skipped = sorted((registered | provided) - processable)

        results: dict[str, PipelineResult] = {}
        verdicts: list[str] = []

        for name in sorted(processable):
            result = self.run_one(name, inputs[name])
            results[name] = result
            verdicts.append(result.pipeline_verdict)

        batch_verdict = (
            max(verdicts, key=lambda v: _VERDICT_RANK.get(v, 0))
            if verdicts
            else "PASS"
        )

        return BatchResult(
            results=results,
            skipped=skipped,
            batch_verdict=batch_verdict,
            run_at=datetime.now(tz=timezone.utc).isoformat(),
        )
