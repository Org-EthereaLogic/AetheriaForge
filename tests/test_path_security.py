"""Direct regression tests for operator path hardening helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from aetheriaforge.path_security import (
    PathSecurityError,
    enforce_configured_dir,
    resolve_configured_child,
    sanitize_log_value,
    validate_simple_filename,
)


def test_enforce_configured_dir_returns_trusted_path_for_blank_request(
    tmp_path: Path,
) -> None:
    trusted = tmp_path / "trusted"
    trusted.mkdir()

    resolved = enforce_configured_dir(
        "",
        configured_dir=trusted,
        context="Evidence directory",
    )

    assert resolved == trusted.resolve()


def test_enforce_configured_dir_resolves_symlink_to_trusted_path(
    tmp_path: Path,
) -> None:
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(trusted, target_is_directory=True)

    resolved = enforce_configured_dir(
        str(alias),
        configured_dir=trusted,
        context="Evidence directory",
    )

    assert resolved == trusted.resolve()


def test_enforce_configured_dir_rejects_blank_configured_path() -> None:
    with pytest.raises(PathSecurityError, match="Configured directory is empty"):
        enforce_configured_dir(
            "",
            configured_dir=" ",
            context="Evidence directory",
        )


def test_enforce_configured_dir_rejects_mismatched_directory(
    tmp_path: Path,
) -> None:
    trusted = tmp_path / "trusted"
    untrusted = tmp_path / "untrusted"
    trusted.mkdir()
    untrusted.mkdir()

    with pytest.raises(PathSecurityError, match="must match the configured directory"):
        enforce_configured_dir(
            str(untrusted),
            configured_dir=trusted,
            context="Evidence directory",
        )


def test_validate_simple_filename_accepts_allowed_json_suffix() -> None:
    assert (
        validate_simple_filename(
            "artifact.JSON",
            context="Artifact filename",
            allowed_suffixes={".json"},
        )
        == "artifact.JSON"
    )


@pytest.mark.parametrize(
    ("filename", "pattern"),
    [
        ("", "is empty"),
        ("../artifact.json", "bare filename"),
        ("nested/artifact.json", "bare filename"),
        ("/tmp/artifact.json", "bare filename"),
        ("artifact.txt", "must use one of: .json"),
    ],
)
def test_validate_simple_filename_rejects_invalid_inputs(
    filename: str,
    pattern: str,
) -> None:
    with pytest.raises(PathSecurityError, match=pattern):
        validate_simple_filename(
            filename,
            context="Artifact filename",
            allowed_suffixes={".json"},
        )


def test_resolve_configured_child_returns_trusted_json_path(
    tmp_path: Path,
) -> None:
    trusted = tmp_path / "trusted"
    trusted.mkdir()

    resolved = resolve_configured_child(
        str(trusted),
        "artifact.json",
        configured_dir=trusted,
        context="Artifact filename",
        allowed_suffixes={".json"},
    )

    assert resolved == trusted.resolve() / "artifact.json"


def test_resolve_configured_child_rejects_untrusted_directory(
    tmp_path: Path,
) -> None:
    trusted = tmp_path / "trusted"
    untrusted = tmp_path / "untrusted"
    trusted.mkdir()
    untrusted.mkdir()

    with pytest.raises(PathSecurityError, match="must match the configured directory"):
        resolve_configured_child(
            str(untrusted),
            "artifact.json",
            configured_dir=trusted,
            context="Artifact filename",
            allowed_suffixes={".json"},
        )


def test_sanitize_log_value_escapes_newlines_and_carriage_returns() -> None:
    assert sanitize_log_value("bad\r\nvalue\n") == "bad\\r\\nvalue\\n"


def test_sanitize_log_value_truncates_long_values() -> None:
    sanitized = sanitize_log_value("x" * 600)
    assert len(sanitized) == 500
    assert sanitized == "x" * 500
