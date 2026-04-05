"""Regression guards for published package metadata surfaces."""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_readme_contains_pypi_badge_and_project_link() -> None:
    raw = (ROOT / "README.md").read_text(encoding="utf-8")

    assert 'href="https://pypi.org/project/etherealogic-aetheriaforge/"' in raw
    assert 'src="https://img.shields.io/pypi/v/etherealogic-aetheriaforge"' in raw
    assert 'alt="PyPI version"' in raw


def test_pyproject_exposes_documentation_url() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    urls = project["urls"]

    assert urls["Documentation"] == "https://github.com/Org-EthereaLogic/AetheriaForge#readme"
