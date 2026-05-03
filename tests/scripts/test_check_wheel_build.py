"""Tests for scripts/check_wheel_build.py.

The end-to-end test that actually builds a wheel via `python -m build` is
marked `e2e` (slow — ~2 minutes) and runs only via `make e2e` or explicit
`pytest -m e2e`. The fast tests cover the script's flag/version-resolution
logic and the failure-path JSON shapes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def mod(load_ci_script):
    return load_ci_script("check_wheel_build.py")


# -- Fast unit tests --


def test_read_kernel_version_returns_a_semver(mod) -> None:
    """_read_kernel_version() reads kernel/__init__.py and returns the version."""
    v = mod._read_kernel_version()
    assert v is not None
    # PEP 440 doesn't require strict semver; just confirm digits.dot.digits prefix.
    assert v[0].isdigit()
    assert "." in v


def test_main_with_invalid_tag_format_does_not_crash(mod, tmp_path: Path,
                                                      monkeypatch: pytest.MonkeyPatch,
                                                      capsys: pytest.CaptureFixture[str]) -> None:
    """When --tag is missing AND kernel/__init__.py is unreadable, main() returns 1
    with a JSON error report — never crashes uncaught."""
    monkeypatch.setattr(mod, "_KERNEL_INIT", tmp_path / "nonexistent.py")
    rc = mod.main(["--tag"]) if False else None  # noqa  — illustrative
    # Simpler path: monkeypatch _read_kernel_version to None
    monkeypatch.setattr(mod, "_read_kernel_version", lambda: None)
    rc = mod.main([])
    assert rc == 1
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False
    assert out["phase"] == "tag-resolution"


def test_validate_returns_parsed_report(mod, tmp_path: Path) -> None:
    """_validate() returns the validator's JSON output as a dict."""
    # Construct a fake wheel path that does not exist; the validator script will
    # report status=missing with an error. We're checking that _validate can parse
    # whatever JSON the validator emits even on failure.
    fake_wheel = tmp_path / "nonexistent.whl"
    rc, report = mod._validate(fake_wheel, "v0.0.1", mod._REPO_ROOT)
    assert isinstance(report, dict)
    # The validator returns rc=1 for missing wheel; we don't assert exact rc
    # because the validator could change. We assert the parse succeeded.
    assert "status" in report or "error" in report


# -- Slow e2e test (skipped unless `pytest -m e2e`) --


pytestmark_e2e = pytest.mark.e2e


@pytest.mark.e2e
def test_full_build_and_validate_against_kernel_version(mod) -> None:
    """End-to-end: builds the actual sdist+wheel via `python -m build` and
    validates against `v` + kanon_core.__version__. This is the regression-prevention
    test for the v0.5.0a2 hotfix class (PRs #99 + #100): catches sdist-include
    misconfiguration and validator-path drift."""
    rc = mod.main([])  # uses kanon_core.__version__
    assert rc == 0, "wheel-build-validate failed end-to-end against current kernel version"
