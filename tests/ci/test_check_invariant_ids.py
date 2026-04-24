"""Tests for ci/check_invariant_ids.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _REPO_ROOT / "ci" / "check_invariant_ids.py"
assert _SCRIPT_PATH.is_file(), f"script not found: {_SCRIPT_PATH}"


def _load():
    spec = importlib.util.spec_from_file_location("check_invariant_ids", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


mod = _load()


def test_real_repo_passes() -> None:
    """The kanon repo itself must pass invariant-id checks."""
    errors, _warnings = mod.check(
        _REPO_ROOT / "docs" / "specs",
        _REPO_ROOT / "docs",
    )
    assert errors == [], "check_invariant_ids failed:\n  " + "\n  ".join(errors)


def test_main_exits_zero_on_ok(capsys: pytest.CaptureFixture[str]) -> None:
    rc = mod.main([
        "--specs", str(_REPO_ROOT / "docs" / "specs"),
        "--docs", str(_REPO_ROOT / "docs"),
    ])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["status"] == "ok"


def test_missing_anchor_detected(tmp_path: Path) -> None:
    """An accepted spec with an invariant but no anchor should error."""
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "bad.md").write_text(
        "---\nstatus: accepted\ndate: 2026-01-01\n---\n# Spec: Bad\n\n"
        "## Invariants\n\n1. **Foo.** Must hold.\n",
        encoding="utf-8",
    )
    errors, _ = mod.check(specs, tmp_path)
    assert len(errors) == 1
    assert "missing INV-* anchor" in errors[0]


def test_duplicate_anchor_detected(tmp_path: Path) -> None:
    """A spec with duplicate INV-* IDs should error."""
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "dup.md").write_text(
        "---\nstatus: accepted\ndate: 2026-01-01\n---\n# Spec: Dup\n\n"
        "## Invariants\n\n"
        "<!-- INV-dup-foo -->\n1. **Foo.** Must hold.\n"
        "<!-- INV-dup-foo -->\n2. **Bar.** Must hold.\n",
        encoding="utf-8",
    )
    errors, _ = mod.check(specs, tmp_path)
    assert any("duplicate anchor" in e for e in errors)
