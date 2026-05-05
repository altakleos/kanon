"""Tests for the bootstrap version check in _run_verify_core."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from kanon_core.cli import _run_verify_core, main


def _init_project(tmp_path: Path) -> Path:
    target = tmp_path / "proj"
    CliRunner().invoke(main, ["init", str(target), "--profile", "solo", "--quiet"])
    return target


def test_version_check_warns_when_stale(tmp_path: Path) -> None:
    """Warning emitted when installed version < kit_version in config."""
    target = _init_project(tmp_path)
    with patch("kanon_core.__version__", "0.3.0"):
        result = _run_verify_core(target)
    assert any("older than this project requires" in w for w in result["warnings"])


def test_version_check_silent_when_current(tmp_path: Path) -> None:
    """No warning when installed version >= kit_version."""
    target = _init_project(tmp_path)
    result = _run_verify_core(target)
    assert not any("older than this project requires" in w for w in result["warnings"])


def test_version_check_prerelease_ordering(tmp_path: Path) -> None:
    """Pre-release versions compare correctly: 0.5.0a3 < 0.5.0a4."""
    target = _init_project(tmp_path)
    with patch("kanon_core.__version__", "0.5.0a3"):
        result = _run_verify_core(target)
    assert any("older than this project requires" in w for w in result["warnings"])


def test_version_check_skip_env_var(tmp_path: Path, monkeypatch: object) -> None:
    """KANON_SKIP_VERSION_CHECK=1 suppresses the warning."""
    target = _init_project(tmp_path)
    monkeypatch.setenv("KANON_SKIP_VERSION_CHECK", "1")  # type: ignore[attr-defined]
    with patch("kanon_core.__version__", "0.3.0"):
        result = _run_verify_core(target)
    assert not any("older than this project requires" in w for w in result["warnings"])
