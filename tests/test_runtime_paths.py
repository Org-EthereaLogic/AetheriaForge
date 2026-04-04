"""Tests for shared Databricks runtime storage helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from aetheriaforge.runtime_paths import (
    DEFAULT_RUNTIME_VOLUME,
    shared_contracts_dir,
    shared_evidence_dir,
    shared_runtime_root,
)


def test_shared_runtime_root_defaults_to_aetheriaforge_volume() -> None:
    assert shared_runtime_root("adb_dev", "default") == Path(
        "/Volumes/adb_dev/default"
    ) / DEFAULT_RUNTIME_VOLUME


def test_shared_contracts_dir_appends_contracts_leaf() -> None:
    assert shared_contracts_dir("adb_dev", "default", "shared") == Path(
        "/Volumes/adb_dev/default/shared/contracts"
    )


def test_shared_evidence_dir_appends_evidence_leaf() -> None:
    assert shared_evidence_dir("adb_dev", "default", "shared") == Path(
        "/Volumes/adb_dev/default/shared/evidence"
    )


def test_shared_runtime_root_rejects_blank_path_parts() -> None:
    with pytest.raises(ValueError):
        shared_runtime_root("", "default")
