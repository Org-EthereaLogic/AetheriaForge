"""Tests for cross-source entity resolution.

Traces: AF-SR-003, AF-FR-007, TP-001 section 3
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from aetheriaforge.evidence import EvidenceWriter
from aetheriaforge.paths import repo_root
from aetheriaforge.resolution import (
    EntityResolver,
    MatchingConfig,
    ResolutionPolicy,
    SourceConfig,
)


def _make_policy(
    strategy: str = "exact",
    ambiguity_behavior: str = "skip",
    sources: tuple[SourceConfig, ...] | None = None,
) -> ResolutionPolicy:
    """Build a minimal ResolutionPolicy for testing."""
    if sources is None:
        sources = (
            SourceConfig(name="primary", key_columns=("entity_id",), priority=1),
            SourceConfig(name="secondary", key_columns=("entity_id",), priority=2),
        )
    return ResolutionPolicy(
        policy_name="test_policy",
        version="1.0.0",
        sources=sources,
        matching=MatchingConfig(
            strategy=strategy,
            confidence_threshold=0.85,
            ambiguity_behavior=ambiguity_behavior,
        ),
        record_all_decisions=True,
        include_rejected_matches=True,
    )


# --- Exact matching tests -----------------------------------------------------


def test_exact_match_single_record() -> None:
    """One primary record matching one secondary record resolves correctly."""
    policy = _make_policy()
    resolver = EntityResolver(policy)

    primary = pd.DataFrame({"entity_id": [1], "name": ["Alice"]})
    secondary = pd.DataFrame({"entity_id": [1], "score": [99]})

    result = resolver.resolve(primary, secondary)

    assert len(result.resolved) == 1
    assert result.resolved_count == 1
    assert result.unresolved_count == 0
    assert len(result.decisions) == 1
    assert result.decisions[0].verdict == "MATCHED"
    assert result.decisions[0].confidence == 1.0


def test_exact_match_no_match() -> None:
    """Primary record with no matching secondary key goes to unresolved."""
    policy = _make_policy()
    resolver = EntityResolver(policy)

    primary = pd.DataFrame({"entity_id": [1], "name": ["Alice"]})
    secondary = pd.DataFrame({"entity_id": [999], "score": [50]})

    result = resolver.resolve(primary, secondary)

    assert len(result.unresolved) == 1
    assert result.unresolved_count == 1
    assert result.resolved_count == 0
    assert result.decisions[0].verdict == "NO_MATCH"
    assert result.decisions[0].confidence == 0.0


def test_exact_match_multiple_secondaries_skip() -> None:
    """Ambiguous match with skip behavior sends record to unresolved."""
    policy = _make_policy(ambiguity_behavior="skip")
    resolver = EntityResolver(policy)

    primary = pd.DataFrame({"entity_id": [1], "name": ["Alice"]})
    secondary = pd.DataFrame({"entity_id": [1, 1], "score": [99, 88]})

    result = resolver.resolve(primary, secondary)

    assert len(result.unresolved) == 1
    assert result.unresolved_count == 1
    assert result.ambiguous_count == 1
    assert result.decisions[0].verdict == "AMBIGUOUS"


def test_exact_match_multiple_secondaries_best_match() -> None:
    """Ambiguous match with best_match takes first secondary row."""
    policy = _make_policy(ambiguity_behavior="best_match")
    resolver = EntityResolver(policy)

    primary = pd.DataFrame({"entity_id": [1], "name": ["Alice"]})
    secondary = pd.DataFrame({"entity_id": [1, 1], "score": [99, 88]})

    result = resolver.resolve(primary, secondary)

    assert len(result.resolved) == 1
    assert result.resolved_count == 1
    assert result.ambiguous_count == 1
    assert result.decisions[0].verdict == "AMBIGUOUS"


def test_exact_match_multiple_secondaries_fail() -> None:
    """Ambiguous match with fail behavior raises ValueError."""
    policy = _make_policy(ambiguity_behavior="fail")
    resolver = EntityResolver(policy)

    primary = pd.DataFrame({"entity_id": [1], "name": ["Alice"]})
    secondary = pd.DataFrame({"entity_id": [1, 1], "score": [99, 88]})

    with pytest.raises(ValueError, match="Ambiguous match for key"):
        resolver.resolve(primary, secondary)


# --- Strategy validation tests ------------------------------------------------


def test_fuzzy_strategy_raises() -> None:
    """A policy with strategy='fuzzy' raises NotImplementedError."""
    policy = _make_policy(strategy="fuzzy")
    resolver = EntityResolver(policy)

    primary = pd.DataFrame({"entity_id": [1], "name": ["Alice"]})
    secondary = pd.DataFrame({"entity_id": [1], "score": [99]})

    with pytest.raises(NotImplementedError, match="Only 'exact' strategy"):
        resolver.resolve(primary, secondary)


# --- Evidence tests -----------------------------------------------------------


def test_resolution_evidence_written(tmp_path: Path) -> None:
    """EntityResolver with EvidenceWriter writes an evidence artifact."""
    policy = _make_policy()
    writer = EvidenceWriter(tmp_path / "evidence")
    resolver = EntityResolver(policy, evidence_writer=writer)

    primary = pd.DataFrame({"entity_id": [1], "name": ["Alice"]})
    secondary = pd.DataFrame({"entity_id": [1], "score": [99]})

    result = resolver.resolve(primary, secondary)

    assert result.evidence_path is not None
    assert Path(result.evidence_path).exists()


# --- Policy validation tests --------------------------------------------------


def test_resolution_requires_two_sources() -> None:
    """Policy with only one source raises ValueError on resolve."""
    single_source = (
        SourceConfig(name="primary", key_columns=("entity_id",), priority=1),
    )
    policy = _make_policy(sources=single_source)
    resolver = EntityResolver(policy)

    primary = pd.DataFrame({"entity_id": [1], "name": ["Alice"]})
    secondary = pd.DataFrame({"entity_id": [1], "score": [99]})

    with pytest.raises(ValueError, match="at least two sources"):
        resolver.resolve(primary, secondary)


def test_resolution_policy_from_yaml() -> None:
    """The shipped resolution_policy.yml template loads correctly."""
    template_path = repo_root() / "templates" / "resolution_policy.yml"
    policy = ResolutionPolicy.from_yaml(template_path)

    assert policy.policy_name == "example_resolution"
    assert policy.version == "1.0.0"
    assert len(policy.sources) == 2
    assert policy.matching.strategy == "exact"


def test_resolution_result_as_dict() -> None:
    """as_dict() returns a dict with event=='resolution_result'."""
    policy = _make_policy()
    resolver = EntityResolver(policy)

    primary = pd.DataFrame({"entity_id": [1], "name": ["Alice"]})
    secondary = pd.DataFrame({"entity_id": [1], "score": [99]})

    result = resolver.resolve(primary, secondary)
    d = result.as_dict()

    assert d["event"] == "resolution_result"
    assert "resolved_count" in d
    assert "unresolved_count" in d
    assert "ambiguous_count" in d
    assert "resolved_at" in d
    assert "decisions" in d
