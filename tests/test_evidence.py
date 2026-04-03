"""Tests for append-only evidence writing.

Traces: AF-SR-008, AF-NFR-002
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aetheriaforge.evidence import EvidenceWriter


class _FixedNameWriter(EvidenceWriter):
    """Writer that always targets the same filename — for collision tests."""

    def write(self, artifact: dict[str, object]) -> Path:
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        path = self.evidence_dir / "forge-evidence-fixed.json"
        if path.exists():
            msg = f"Append-only violation: evidence artifact already exists at {path}"
            raise RuntimeError(msg)
        path.write_text(json.dumps(artifact))
        return path


def test_write_creates_file(tmp_path: Path) -> None:
    """Writing an artifact creates a .json file on disk."""
    writer = EvidenceWriter(tmp_path / "evidence")
    path = writer.write({"event": "test"})

    assert path.exists()
    assert path.suffix == ".json"


def test_write_content_is_valid_json(tmp_path: Path) -> None:
    """Written content round-trips through json.loads."""
    writer = EvidenceWriter(tmp_path / "evidence")
    path = writer.write({"key": "value", "n": 42})

    parsed = json.loads(path.read_text())
    assert parsed["key"] == "value"
    assert parsed["n"] == 42


def test_write_creates_unique_files(tmp_path: Path) -> None:
    """Five consecutive writes produce five distinct files."""
    writer = EvidenceWriter(tmp_path / "evidence")
    paths = [writer.write({"i": i}) for i in range(5)]

    assert len(set(paths)) == 5
    for p in paths:
        assert p.exists()


def test_append_only_raises_on_collision(tmp_path: Path) -> None:
    """Pre-existing file triggers RuntimeError with 'Append-only violation'."""
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "forge-evidence-fixed.json").write_text("{}")

    writer = _FixedNameWriter(evidence_dir)

    with pytest.raises(RuntimeError, match="Append-only violation"):
        writer.write({"event": "collision"})


def test_evidence_dir_created_if_missing(tmp_path: Path) -> None:
    """Writer creates a deeply nested evidence directory if it does not exist."""
    deep_dir = tmp_path / "a" / "b" / "c" / "evidence"
    writer = EvidenceWriter(deep_dir)
    path = writer.write({"event": "deep"})

    assert deep_dir.exists()
    assert path.exists()
