"""Shared Databricks runtime storage path helpers."""

from __future__ import annotations

from pathlib import Path

DEFAULT_RUNTIME_VOLUME = "aetheriaforge_runtime"


def _clean_part(value: str, *, label: str) -> str:
    """Return a stripped path part or raise when it is blank."""
    cleaned = value.strip()
    if not cleaned:
        msg = f"{label} is required to build a shared runtime path"
        raise ValueError(msg)
    return cleaned


def shared_runtime_root(
    catalog: str,
    schema: str,
    volume: str = DEFAULT_RUNTIME_VOLUME,
) -> Path:
    """Return the shared Unity Catalog volume root used by apps and jobs."""
    return Path("/Volumes") / _clean_part(catalog, label="catalog") / _clean_part(
        schema, label="schema"
    ) / _clean_part(volume, label="volume")


def shared_contracts_dir(
    catalog: str,
    schema: str,
    volume: str = DEFAULT_RUNTIME_VOLUME,
) -> Path:
    """Return the shared contracts directory."""
    return shared_runtime_root(catalog, schema, volume) / "contracts"


def shared_evidence_dir(
    catalog: str,
    schema: str,
    volume: str = DEFAULT_RUNTIME_VOLUME,
) -> Path:
    """Return the shared evidence directory."""
    return shared_runtime_root(catalog, schema, volume) / "evidence"
