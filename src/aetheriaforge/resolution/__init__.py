"""AetheriaForge resolution module."""

from aetheriaforge.resolution.policy import (
    MatchingConfig,
    ResolutionPolicy,
    SourceConfig,
)
from aetheriaforge.resolution.resolver import (
    EntityResolver,
    MatchDecision,
    ResolutionResult,
)

__all__ = [
    "EntityResolver",
    "MatchDecision",
    "MatchingConfig",
    "ResolutionPolicy",
    "ResolutionResult",
    "SourceConfig",
]
