"""Append-only evidence artifact writer."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class EvidenceWriter:
    """Write transformation evidence artifacts to an append-only directory.

    Each artifact is written as a uniquely-named JSON file.  If a file with the
    generated name already exists, a ``RuntimeError`` is raised to enforce the
    append-only invariant.
    """

    def __init__(self, evidence_dir: Path) -> None:
        self.evidence_dir = evidence_dir

    def write(self, artifact: dict[str, Any]) -> Path:
        """Serialize *artifact* to a new JSON evidence file and return its path.

        Raises ``RuntimeError`` if the target file already exists (append-only
        violation).
        """
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(tz=timezone.utc)
        filename = f"forge-evidence-{now.strftime('%Y%m%dT%H%M%S')}_{now.strftime('%f')}.json"
        path = self.evidence_dir / filename
        if path.exists():
            msg = f"Append-only violation: evidence artifact already exists at {path}"
            raise RuntimeError(msg)
        path.write_text(json.dumps(artifact, default=str))
        return path
