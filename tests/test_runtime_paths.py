"""Tests for shared Databricks runtime storage helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from aetheriaforge.runtime_paths import (
    DEFAULT_LOCAL_APP_DIRNAME,
    DEFAULT_RUNTIME_VOLUME,
    default_contracts_dir,
    default_evidence_dir,
    local_app_root,
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


def test_local_app_root_defaults_under_home_directory(tmp_path: Path) -> None:
    assert local_app_root(tmp_path) == tmp_path / DEFAULT_LOCAL_APP_DIRNAME


def test_default_contracts_dir_uses_local_app_root(tmp_path: Path) -> None:
    assert default_contracts_dir(tmp_path) == tmp_path / DEFAULT_LOCAL_APP_DIRNAME / "contracts"


def test_default_evidence_dir_uses_local_app_root(tmp_path: Path) -> None:
    assert default_evidence_dir(tmp_path) == tmp_path / DEFAULT_LOCAL_APP_DIRNAME / "evidence"


def test_shared_runtime_root_rejects_blank_path_parts() -> None:
    with pytest.raises(ValueError):
        shared_runtime_root("", "default")
