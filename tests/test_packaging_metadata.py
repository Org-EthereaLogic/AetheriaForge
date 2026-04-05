"""Regression guards for package metadata and publish workflow wiring."""

from __future__ import annotations

import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def test_pyproject_exposes_repository_and_pypi_urls() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]

    assert project["name"] == "etherealogic-aetheriaforge"
    assert project["license"]["text"] == "MIT"
    urls = project["urls"]
    assert urls["Homepage"] == "https://github.com/Org-EthereaLogic/AetheriaForge"
    assert urls["Repository"] == "https://github.com/Org-EthereaLogic/AetheriaForge"
    assert urls["PyPI"] == "https://pypi.org/project/etherealogic-aetheriaforge/"
    assert urls["Issues"] == "https://github.com/Org-EthereaLogic/AetheriaForge/issues"


def test_publish_workflow_uploads_pypi_storage_records() -> None:
    workflow = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "publish.yml").read_text(encoding="utf-8")
    )

    assert workflow["permissions"]["artifact-metadata"] == "write"
    steps = workflow["jobs"]["publish"]["steps"]
    step_names = [step.get("name") for step in steps]
    assert "Publish to PyPI" in step_names
    assert "Upload PyPI storage records to GitHub linked artifacts" in step_names

    upload_step = next(
        step
        for step in steps
        if step.get("name") == "Upload PyPI storage records to GitHub linked artifacts"
    )
    run = upload_step["run"]
    assert "artifact_url" in run
    assert "github_repository" in run
    assert "artifacts/metadata/storage-record" in run
