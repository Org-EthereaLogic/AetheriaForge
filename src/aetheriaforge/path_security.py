"""Path and log hardening helpers for operator-controlled inputs."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable


class PathSecurityError(ValueError):
    """Raised when operator-controlled path input violates the trust boundary."""


def _normalize_path_text(value: str | Path) -> str:
    """Return a normalized absolute path string without touching the filesystem."""
    text = os.fspath(value).strip()
    if not text:
        raise PathSecurityError("Configured directory is empty.")
    return os.path.realpath(os.path.expanduser(text))


def enforce_configured_dir(
    requested_dir: str,
    *,
    configured_dir: str | Path,
    context: str,
) -> Path:
    """Allow only the preconfigured directory for a sensitive read surface."""
    configured_norm = _normalize_path_text(configured_dir)
    requested = requested_dir.strip()
    if requested:
        requested_norm = _normalize_path_text(requested)
        if requested_norm != configured_norm:
            raise PathSecurityError(
                f"{context} must match the configured directory: {configured_norm}"
            )
    return Path(configured_norm)


def validate_simple_filename(
    filename: str,
    *,
    context: str,
    allowed_suffixes: Iterable[str] | None = None,
) -> str:
    """Accept only a bare filename, never a nested or absolute path."""
    name = filename.strip()
    if not name:
        raise PathSecurityError(f"{context} is empty.")

    normalized = os.path.normpath(name)
    parts = Path(name).parts
    if os.path.isabs(name) or normalized != name or len(parts) != 1 or Path(name).name != name:
        raise PathSecurityError(f"{context} must be a bare filename.")

    if allowed_suffixes is not None:
        suffixes = {suffix.lower() for suffix in allowed_suffixes}
        if Path(name).suffix.lower() not in suffixes:
            expected = ", ".join(sorted(suffixes))
            raise PathSecurityError(f"{context} must use one of: {expected}")

    return name


def resolve_configured_child(
    requested_dir: str,
    child_name: str,
    *,
    configured_dir: str | Path,
    context: str,
    allowed_suffixes: Iterable[str] | None = None,
) -> Path:
    """Resolve a sanitized child filename under a configured trusted directory."""
    root = enforce_configured_dir(
        requested_dir,
        configured_dir=configured_dir,
        context=f"{context} directory",
    )
    name = validate_simple_filename(
        child_name,
        context=context,
        allowed_suffixes=allowed_suffixes,
    )
    return root / name


def sanitize_log_value(value: object) -> str:
    """Strip control characters so user-controlled values cannot forge log lines."""
    text = str(value)
    sanitized = text.replace("\r", "\\r").replace("\n", "\\n")
    return sanitized[:500]
