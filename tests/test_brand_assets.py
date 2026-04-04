"""Regression tests for the AetheriaForge brand asset package."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
BRAND_ROOT = ROOT / "assets" / "aetheriaforge-brand-system"

EXPECTED_GENERATED_COUNTS = {
    "source": 3,
    "icons": 4,
    "variants": 6,
    "favicons": 9,
    "social": 3,
}


def test_brand_system_files_exist() -> None:
    required = [
        BRAND_ROOT / "README.md",
        BRAND_ROOT / "generate_brand_assets.py",
        BRAND_ROOT / "source" / "aetheriaforge-mark-source.svg",
        BRAND_ROOT / "source" / "aetheriaforge-logo-source.svg",
        BRAND_ROOT / "variants" / "logo-light.png",
        BRAND_ROOT / "variants" / "logo-dark.png",
        BRAND_ROOT / "favicons" / "favicon.ico",
        BRAND_ROOT / "favicons" / "site.webmanifest",
        BRAND_ROOT / "social" / "og-image.png",
    ]

    for path in required:
        assert path.is_file(), f"Missing brand asset: {path.relative_to(ROOT)}"
        assert path.stat().st_size > 0, f"Empty brand asset: {path.relative_to(ROOT)}"


def test_generated_asset_inventory_matches_documented_counts() -> None:
    counts = {
        name: sum(1 for path in (BRAND_ROOT / name).iterdir() if path.is_file())
        for name in EXPECTED_GENERATED_COUNTS
    }

    assert counts == EXPECTED_GENERATED_COUNTS
    assert sum(counts.values()) == 25
    assert sum(1 for path in BRAND_ROOT.rglob("*") if path.is_file()) == 27


def test_brand_image_dimensions_match_expected_exports() -> None:
    expected_sizes = {
        "icons/aetheriaforge-mark-128.png": (128, 128),
        "icons/aetheriaforge-mark-256.png": (256, 256),
        "icons/aetheriaforge-mark-512.png": (512, 512),
        "icons/aetheriaforge-logo-1200x320.png": (1200, 320),
        "social/og-image.png": (1200, 630),
        "social/twitter-card.png": (1200, 600),
        "social/linkedin-banner.png": (1584, 396),
    }

    for relative_path, size in expected_sizes.items():
        with Image.open(BRAND_ROOT / relative_path) as image:
            assert image.size == size, f"Unexpected export size for {relative_path}"


def test_web_manifest_matches_exported_icons() -> None:
    manifest = json.loads((BRAND_ROOT / "favicons" / "site.webmanifest").read_text(encoding="utf-8"))

    assert manifest["name"] == "AetheriaForge"
    assert manifest["short_name"] == "AetheriaForge"
    assert manifest["theme_color"] == "#0D1B2A"
    assert manifest["background_color"] == "#0D1B2A"

    icon_sources = {item["src"] for item in manifest["icons"]}
    assert icon_sources == {"android-chrome-192x192.png", "android-chrome-512x512.png"}
