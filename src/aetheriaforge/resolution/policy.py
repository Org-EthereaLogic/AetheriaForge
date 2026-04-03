"""Resolution policy configuration loaded from YAML."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SourceConfig:
    """A single source definition in a resolution policy."""

    name: str
    key_columns: tuple[str, ...]
    priority: int


@dataclass(frozen=True)
class MatchingConfig:
    """Matching configuration for entity resolution."""

    strategy: str
    confidence_threshold: float
    ambiguity_behavior: str


@dataclass(frozen=True)
class ResolutionPolicy:
    """Immutable resolution policy loaded from YAML.

    Defines sources, matching strategy, and evidence preferences for
    cross-source entity resolution.
    """

    policy_name: str
    version: str
    sources: tuple[SourceConfig, ...]
    matching: MatchingConfig
    record_all_decisions: bool
    include_rejected_matches: bool

    @property
    def sources_list(self) -> list[SourceConfig]:
        """Return sources as a mutable list for caller convenience."""
        return list(self.sources)

    @classmethod
    def from_yaml(cls, path: Path) -> ResolutionPolicy:
        """Load a ResolutionPolicy from a YAML file on disk."""
        with open(path) as fh:
            data = yaml.safe_load(fh)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResolutionPolicy:
        """Construct a ResolutionPolicy from a parsed YAML dictionary."""
        for section in ("policy", "sources", "matching", "evidence"):
            if section not in data:
                msg = f"Resolution policy missing required section: '{section}'"
                raise ValueError(msg)

        policy = data["policy"]
        sources_raw = data["sources"]
        matching_raw = data["matching"]
        evidence_raw = data["evidence"]

        sources = tuple(
            SourceConfig(
                name=str(s["name"]),
                key_columns=tuple(str(k) for k in s.get("key_columns", [])),
                priority=int(s.get("priority", 0)),
            )
            for s in sources_raw
        )

        matching = MatchingConfig(
            strategy=str(matching_raw.get("strategy", "exact")),
            confidence_threshold=float(matching_raw.get("confidence_threshold", 0.85)),
            ambiguity_behavior=str(matching_raw.get("ambiguity_behavior", "skip")),
        )

        return cls(
            policy_name=str(policy["name"]),
            version=str(policy.get("version", "0.0.0")),
            sources=sources,
            matching=matching,
            record_all_decisions=bool(evidence_raw.get("record_all_decisions", True)),
            include_rejected_matches=bool(
                evidence_raw.get("include_rejected_matches", True)
            ),
        )
