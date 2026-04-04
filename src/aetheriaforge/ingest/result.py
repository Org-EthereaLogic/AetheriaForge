"""Ingestion result dataclass with evidence support."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from aetheriaforge.ingest.formats import FileFormat


@dataclass
class IngestResult:
    """Outcome of a file ingestion operation."""

    df: pd.DataFrame
    file_path: str
    file_format: FileFormat
    records_read: int
    columns: list[str]
    file_size_bytes: int
    ingested_at: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    options_applied: dict[str, Any] = field(default_factory=dict)
    evidence_path: str | None = None

    @property
    def ok(self) -> bool:
        """Return True if ingestion completed without errors."""
        return len(self.errors) == 0

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary for evidence writing."""
        return {
            "event": "ingest_result",
            "file_path": self.file_path,
            "file_format": self.file_format.value,
            "records_read": self.records_read,
            "columns": self.columns,
            "file_size_bytes": self.file_size_bytes,
            "ingested_at": self.ingested_at,
            "errors": self.errors,
            "warnings": self.warnings,
            "options_applied": self.options_applied,
            "evidence_path": self.evidence_path,
        }
