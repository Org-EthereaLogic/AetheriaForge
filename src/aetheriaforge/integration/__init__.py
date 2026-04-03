"""AetheriaForge integration module — optional DriftSentinel interface.

This module is inactive by default.  Enable it through bundled-mode
configuration when both ÆtheriaForge and DriftSentinel are deployed in the
same Databricks workspace.
"""

from aetheriaforge.integration.config import BundledModeConfig, discover_bundled_config
from aetheriaforge.integration.drift import (
    ColumnDriftReport,
    DriftIngester,
    DriftReport,
    RemediationAction,
)
from aetheriaforge.integration.events import (
    EventChannel,
    FileEventChannel,
    NullEventChannel,
    TransformationEvent,
)

__all__ = [
    "BundledModeConfig",
    "ColumnDriftReport",
    "DriftIngester",
    "DriftReport",
    "EventChannel",
    "FileEventChannel",
    "NullEventChannel",
    "RemediationAction",
    "TransformationEvent",
    "discover_bundled_config",
]
