"""Bundled-mode configuration for optional DriftSentinel integration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class BundledModeConfig:
    """Configuration for the DriftSentinel integration layer.

    When ``enabled`` is ``False`` (the default), the integration layer is
    inactive and ÆtheriaForge operates in standalone mode.
    """

    enabled: bool = False
    events_dir: str = ""
    drift_dir: str = ""
    auto_ingest: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BundledModeConfig:
        """Construct from a parsed dictionary (typically the ``integration`` section)."""
        return cls(
            enabled=bool(data.get("enabled", False)),
            events_dir=str(data.get("events_dir", "")),
            drift_dir=str(data.get("drift_dir", "")),
            auto_ingest=bool(data.get("auto_ingest", False)),
        )

    @classmethod
    def from_yaml(cls, path: Path) -> BundledModeConfig:
        """Load from a YAML file containing an ``integration`` section."""
        with open(path) as fh:
            raw = yaml.safe_load(fh)
        section = raw.get("integration", {}) if raw else {}
        return cls.from_dict(section)

    @classmethod
    def disabled(cls) -> BundledModeConfig:
        """Return the standalone-mode default (integration off)."""
        return cls(enabled=False)


def discover_bundled_config(
    contract_raw: dict[str, Any] | None = None,
    config_path: Path | None = None,
) -> BundledModeConfig:
    """Resolve bundled-mode configuration from a contract dict or standalone file.

    Returns ``BundledModeConfig.disabled()`` if neither source provides
    integration configuration.
    """
    if config_path is not None and config_path.exists():
        return BundledModeConfig.from_yaml(config_path)

    if contract_raw is not None and "integration" in contract_raw:
        return BundledModeConfig.from_dict(contract_raw["integration"])

    return BundledModeConfig.disabled()
