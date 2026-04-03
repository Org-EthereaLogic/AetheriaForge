"""Event emission interface for DriftSentinel integration."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class TransformationEvent:
    """Immutable representation of a transformation event for cross-product exchange.

    ÆtheriaForge owns this type — it does not import DriftSentinel types.
    """

    event_type: str
    dataset_name: str
    dataset_version: str
    coherence_score: float | None
    verdict: str
    resolution_outcome: str | None
    schema_version: str | None
    run_at: str
    payload: dict[str, Any]

    @classmethod
    def from_pipeline_result(
        cls,
        result: Any,
        contract: Any,
    ) -> TransformationEvent:
        """Build a :class:`TransformationEvent` from a ``PipelineResult`` and ``ForgeContract``."""
        payload = result.as_dict()
        resolution_outcome: str | None = None
        if result.resolution_result is not None:
            resolved_count = len(result.resolution_result.resolved)
            resolution_outcome = "resolved" if resolved_count > 0 else "unresolved"

        return cls(
            event_type=payload.get("event", "pipeline_result"),
            dataset_name=result.dataset_name,
            dataset_version=contract.dataset_version,
            coherence_score=result.forge_result.coherence_score,
            verdict=result.pipeline_verdict,
            resolution_outcome=resolution_outcome,
            schema_version=contract.dataset_version,
            run_at=result.run_at,
            payload=payload,
        )


@runtime_checkable
class EventChannel(Protocol):
    """Protocol for transformation event channels."""

    def emit(self, event: TransformationEvent) -> None:
        """Emit a transformation event."""
        ...


class NullEventChannel:
    """No-op channel used when integration is disabled (standalone mode)."""

    def emit(self, event: TransformationEvent) -> None:
        """Accept and discard the event."""


class FileEventChannel:
    """Write transformation events as JSON files to a shared directory.

    Mirrors the ``EvidenceWriter`` pattern: timestamped filenames with an
    append-only guard.
    """

    def __init__(self, events_dir: Path) -> None:
        self.events_dir = events_dir

    def emit(self, event: TransformationEvent) -> None:
        """Serialize *event* to a new JSON file in the events directory."""
        self.events_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(tz=timezone.utc)
        filename = f"af-event-{now.strftime('%Y%m%dT%H%M%S')}_{now.strftime('%f')}.json"
        path = self.events_dir / filename
        if path.exists():
            msg = f"Append-only violation: event file already exists at {path}"
            raise RuntimeError(msg)
        path.write_text(json.dumps(asdict(event), default=str))
