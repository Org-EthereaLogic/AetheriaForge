"""Drift payload ingestion interface for DriftSentinel integration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aetheriaforge.config.registry import DatasetRegistry
from aetheriaforge.evidence.writer import EvidenceWriter


@dataclass(frozen=True)
class ColumnDriftReport:
    """Single-column drift report received from DriftSentinel.

    ÆtheriaForge owns this type — it does not import DriftSentinel types.
    """

    column: str
    baseline_score: float
    current_score: float
    delta: float
    classification: str  # "STABLE" | "COLLAPSED" | "SPIKED"


@dataclass(frozen=True)
class DriftReport:
    """Aggregate drift report for one dataset, parsed from a JSON payload.

    Mirrors the DriftSentinel ``DriftResult`` shape without importing it.
    """

    dataset_name: str
    health_score: float
    columns_checked: int
    columns_drifted: int
    schema_match: bool
    gate_verdict: str  # "PASS" | "WARN" | "FAIL"
    column_reports: tuple[ColumnDriftReport, ...] = ()
    received_at: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DriftReport:
        """Parse a DriftSentinel-shaped JSON dictionary into a :class:`DriftReport`."""
        col_reports = tuple(
            ColumnDriftReport(
                column=str(cr.get("column", "")),
                baseline_score=float(cr.get("baseline_score", 0.0)),
                current_score=float(cr.get("current_score", 0.0)),
                delta=float(cr.get("delta", 0.0)),
                classification=str(cr.get("classification", "STABLE")),
            )
            for cr in data.get("column_reports", [])
        )
        return cls(
            dataset_name=str(data.get("dataset_name", "")),
            health_score=float(data.get("health_score", 0.0)),
            columns_checked=int(data.get("columns_checked", 0)),
            columns_drifted=int(data.get("columns_drifted", 0)),
            schema_match=bool(data.get("schema_match", True)),
            gate_verdict=str(data.get("gate_verdict", "PASS")),
            column_reports=col_reports,
            received_at=str(data.get("received_at", "")),
        )


@dataclass(frozen=True)
class RemediationAction:
    """Describes what remediation was triggered for a drift report."""

    dataset_name: str
    drift_health_score: float
    drift_gate_verdict: str
    action: str  # "re_score" | "flag_only" | "skip"
    reason: str
    actioned_at: str

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary."""
        return {
            "event": "remediation_action",
            "dataset_name": self.dataset_name,
            "drift_health_score": self.drift_health_score,
            "drift_gate_verdict": self.drift_gate_verdict,
            "action": self.action,
            "reason": self.reason,
            "actioned_at": self.actioned_at,
        }


class DriftIngester:
    """Ingest drift reports from a shared directory and route into remediation.

    Reads ``ds-drift-*.json`` files from *drift_dir*, parses them into
    :class:`DriftReport` instances, and routes each into a
    :class:`RemediationAction` based on registry membership and gate verdict.
    """

    def __init__(
        self,
        drift_dir: Path,
        registry: DatasetRegistry,
        evidence_writer: EvidenceWriter | None = None,
    ) -> None:
        self.drift_dir = drift_dir
        self.registry = registry
        self.evidence_writer = evidence_writer

    def scan(self) -> list[DriftReport]:
        """Read all unprocessed drift report JSON files from *drift_dir*."""
        if not self.drift_dir.exists():
            return []
        reports: list[DriftReport] = []
        for path in sorted(self.drift_dir.glob("ds-drift-*.json")):
            raw = json.loads(path.read_text())
            reports.append(DriftReport.from_dict(raw))
        return reports

    def ingest(self, report: DriftReport) -> RemediationAction:
        """Route a single drift report into a remediation action."""
        now_utc = datetime.now(tz=timezone.utc).isoformat()

        if report.dataset_name not in self.registry:
            action = RemediationAction(
                dataset_name=report.dataset_name,
                drift_health_score=report.health_score,
                drift_gate_verdict=report.gate_verdict,
                action="skip",
                reason="Dataset not registered in forge registry",
                actioned_at=now_utc,
            )
        elif report.gate_verdict in ("WARN", "FAIL"):
            action = RemediationAction(
                dataset_name=report.dataset_name,
                drift_health_score=report.health_score,
                drift_gate_verdict=report.gate_verdict,
                action="re_score",
                reason=f"Drift gate verdict {report.gate_verdict} — re-score recommended",
                actioned_at=now_utc,
            )
        else:
            action = RemediationAction(
                dataset_name=report.dataset_name,
                drift_health_score=report.health_score,
                drift_gate_verdict=report.gate_verdict,
                action="flag_only",
                reason="Drift below gate threshold — flagged for review",
                actioned_at=now_utc,
            )

        if self.evidence_writer is not None:
            self.evidence_writer.write(action.as_dict())

        return action

    def ingest_all(self) -> list[RemediationAction]:
        """Scan and ingest all pending drift reports.

        After processing, each drift file is renamed with a ``.processed``
        suffix to prevent re-ingestion.
        """
        actions: list[RemediationAction] = []
        if not self.drift_dir.exists():
            return actions

        for path in sorted(self.drift_dir.glob("ds-drift-*.json")):
            raw = json.loads(path.read_text())
            report = DriftReport.from_dict(raw)
            action = self.ingest(report)
            actions.append(action)
            path.rename(path.with_suffix(".json.processed"))

        return actions
