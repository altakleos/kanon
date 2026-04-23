"""Tests for ci/check_kit_consistency.py against the real repo."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_VALIDATOR_PATH = _REPO_ROOT / "ci" / "check_kit_consistency.py"
assert _VALIDATOR_PATH.is_file(), f"validator not found: {_VALIDATOR_PATH}"


def _load_validator():
    spec = importlib.util.spec_from_file_location("check_kit_consistency", _VALIDATOR_PATH)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


ckc = _load_validator()


def test_real_repo_passes() -> None:
    """The kanon repo itself must satisfy kit-consistency invariants."""
    errors = ckc.run_checks()
    assert errors == [], "kit-consistency check failed:\n  " + "\n  ".join(errors)


def test_main_exits_zero_on_ok(capsys: pytest.CaptureFixture[str]) -> None:
    rc = ckc.main([])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["status"] == "ok"
