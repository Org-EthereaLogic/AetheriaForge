"""Transformation history — query interface over evidence artifacts."""

from __future__ import annotations

import concurrent.futures
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _ArtifactCacheEntry:
    """Cached parsed artifacts for one evidence directory snapshot."""

    signature: tuple[tuple[str, int, int], ...]
    artifacts: tuple[dict[str, Any], ...]


class TransformationHistory:
    """Read-only query interface over the evidence directory.

    Parses ``forge-evidence-*.json`` files written by :class:`EvidenceWriter`
    and supports filtering by dataset name, verdict, and time range.
    """

    def __init__(self, evidence_dir: Path) -> None:
        self.evidence_dir = evidence_dir

    _cache: dict[str, _ArtifactCacheEntry] = {}
    _cache_lock = Lock()

    def _artifact_paths(self) -> list[Path]:
        """Return candidate JSON artifact paths sorted newest-first by name."""
        if not self.evidence_dir.is_dir():
            return []
        return [
            path for path in sorted(self.evidence_dir.iterdir(), reverse=True)
            if path.suffix == ".json"
        ]

    @staticmethod
    def _directory_signature(paths: list[Path]) -> tuple[tuple[str, int, int], ...]:
        """Build a cache signature from path name, mtime, and size."""
        signature: list[tuple[str, int, int]] = []
        for path in paths:
            stat = path.stat()
            signature.append((path.name, stat.st_mtime_ns, stat.st_size))
        return tuple(signature)

    # -- core read ------------------------------------------------------------

    def _parse_artifact(self, path: Path) -> dict[str, Any] | None:
        """Parse a single evidence JSON file, returning None if malformed."""
        try:
            data = json.loads(path.read_text())
            data["_evidence_path"] = str(path)
            return data  # type: ignore[no-any-return]
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Skipping malformed evidence file %s: %s", path, exc)
            return None

    def _load_artifacts(self) -> list[dict[str, Any]]:
        """Load and parse all evidence JSON files, skipping malformed ones."""
        paths = self._artifact_paths()
        if not paths:
            return []

        cache_key = str(self.evidence_dir.resolve())
        signature = self._directory_signature(paths)

        with self._cache_lock:
            cached = self._cache.get(cache_key)
            if cached is not None and cached.signature == signature:
                return list(cached.artifacts)

        artifacts: list[dict[str, Any]] = []

        with concurrent.futures.ThreadPoolExecutor() as executor:
            for result in executor.map(self._parse_artifact, paths):
                if result is not None:
                    artifacts.append(result)

        with self._cache_lock:
            self._cache[cache_key] = _ArtifactCacheEntry(
                signature=signature,
                artifacts=tuple(artifacts),
            )

        return artifacts

    # -- queries --------------------------------------------------------------

    def list_all(self) -> list[dict[str, Any]]:
        """Return all evidence records sorted by file name descending."""
        return self._load_artifacts()

    def query(
        self,
        *,
        dataset_name: str | None = None,
        verdict: str | None = None,
        after: datetime | None = None,
        before: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Filter evidence records by optional criteria.

        Parameters
        ----------
        dataset_name:
            Match the ``dataset_name`` field in the artifact.
        verdict:
            Match ``pipeline_verdict`` or ``verdict`` fields.
        after:
            Include only artifacts with ``run_at`` or ``forged_at`` on or
            after this datetime.
        before:
            Include only artifacts with ``run_at`` or ``forged_at`` on or
            before this datetime.
        """
        results: list[dict[str, Any]] = []

        for artifact in self._load_artifacts():
            if dataset_name is not None:
                if artifact.get("dataset_name") != dataset_name:
                    continue

            if verdict is not None:
                art_verdict = artifact.get(
                    "pipeline_verdict", artifact.get("verdict")
                )
                if art_verdict != verdict:
                    continue

            if after is not None or before is not None:
                ts_str = artifact.get("run_at") or artifact.get("forged_at")
                if ts_str is None:
                    continue
                try:
                    ts = datetime.fromisoformat(str(ts_str))
                except ValueError:
                    continue
                if after is not None and ts < after:
                    continue
                if before is not None and ts > before:
                    continue

            results.append(artifact)

        return results

    # -- summary --------------------------------------------------------------

    def summary(self) -> dict[str, dict[str, int]]:
        """Return verdict counts grouped by dataset name.

        Returns a dict of ``{dataset_name: {verdict: count}}``.
        """
        counts: dict[str, dict[str, int]] = {}

        for artifact in self._load_artifacts():
            ds = artifact.get("dataset_name", "_unknown")
            v = artifact.get("pipeline_verdict", artifact.get("verdict", "_unknown"))
            bucket = counts.setdefault(str(ds), {})
            bucket[str(v)] = bucket.get(str(v), 0) + 1

        return counts
