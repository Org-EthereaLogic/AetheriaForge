"""Canonical path resolution for AetheriaForge."""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    """Return the repository root directory."""
    return Path(__file__).resolve().parent.parent.parent


def specs_dir() -> Path:
    """Return the canonical specs directory."""
    return repo_root() / "specs"


def templates_dir() -> Path:
    """Return the templates directory."""
    return repo_root() / "templates"


def report_dir() -> Path:
    """Return the append-only report directory."""
    return repo_root() / "report"
