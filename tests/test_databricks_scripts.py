"""Regression tests for Databricks deployment helper scripts."""

from __future__ import annotations

from typing import Any

import scripts.bootstrap_databricks as bootstrap_module
import scripts.deploy_databricks_app as app_deploy_module


def test_bootstrap_bundle_deploy_passes_schema_and_runtime_volume(
    monkeypatch: Any,
) -> None:
    commands: list[list[str]] = []

    def _capture(cmd: list[str], **_: Any) -> None:
        commands.append(cmd)

    monkeypatch.setattr(bootstrap_module, "_run_cli", _capture)

    bootstrap_module._bundle_deploy(
        "test-profile",
        "dev",
        "main_catalog",
        schema="ops",
        volume="af_runtime",
    )

    assert commands == [[
        "databricks",
        "bundle",
        "deploy",
        "--target",
        "dev",
        "--var=catalog=main_catalog",
        "--var=schema=ops",
        "--var=runtime_volume=af_runtime",
        "-p",
        "test-profile",
    ]]


def test_bootstrap_trigger_job_passes_schema_volume_and_contract_path(
    monkeypatch: Any,
) -> None:
    commands: list[list[str]] = []

    def _capture(cmd: list[str], **_: Any) -> None:
        commands.append(cmd)

    monkeypatch.setattr(bootstrap_module, "_run_cli", _capture)

    bootstrap_module._trigger_job(
        "test-profile",
        "dev",
        "main_catalog",
        schema="ops",
        volume="af_runtime",
        contract_path="/Volumes/main_catalog/ops/af_runtime/contracts/forge_contract.yml",
    )

    assert commands == [[
        "databricks",
        "bundle",
        "run",
        "forge_job",
        "--target",
        "dev",
        "--var=catalog=main_catalog",
        "--var=schema=ops",
        "--var=runtime_volume=af_runtime",
        "--var=contract_path=/Volumes/main_catalog/ops/af_runtime/contracts/forge_contract.yml",
        "-p",
        "test-profile",
    ]]


def test_app_deploy_bundle_args_include_schema_and_runtime_volume() -> None:
    args = app_deploy_module._bundle_flag_args(
        "test-profile",
        "dev",
        "main_catalog",
        schema="ops",
        volume="af_runtime",
    )

    assert args == [
        "-p",
        "test-profile",
        "--target",
        "dev",
        "--var=catalog=main_catalog",
        "--var=schema=ops",
        "--var=runtime_volume=af_runtime",
    ]
