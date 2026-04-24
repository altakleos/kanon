"""Tests for ci/check_verified_by.py."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _REPO_ROOT / "ci" / "check_verified_by.py"
assert _SCRIPT_PATH.is_file(), f"script not found: {_SCRIPT_PATH}"


def _load():
    spec = importlib.util.spec_from_file_location("check_verified_by", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


mod = _load()


def test_real_repo_passes() -> None:
    """The kanon repo itself must pass verified-by checks."""
    errors, _warnings = mod.check(
        _REPO_ROOT / "docs" / "specs",
        _REPO_ROOT,
    )
    assert errors == [], "check_verified_by failed:\n  " + "\n  ".join(errors)


def test_main_exits_zero_on_ok(capsys: pytest.CaptureFixture[str]) -> None:
    rc = mod.main([
        "--specs", str(_REPO_ROOT / "docs" / "specs"),
        "--repo-root", str(_REPO_ROOT),
    ])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["status"] == "ok"


def test_missing_coverage_detected(tmp_path: Path) -> None:
    """An accepted spec with an INV anchor but no invariant_coverage should error."""
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "bad.md").write_text(
        "---\nstatus: accepted\ndate: 2026-01-01\n"
        "fixtures: [tests/foo.py]\n---\n# Spec: Bad\n\n"
        "## Invariants\n\n<!-- INV-bad-foo -->\n1. **Foo.** Must hold.\n",
        encoding="utf-8",
    )
    errors, _ = mod.check(specs, tmp_path)
    assert len(errors) == 1
    assert "missing from invariant_coverage" in errors[0]


def test_stale_entry_detected(tmp_path: Path) -> None:
    """A spec with an invariant_coverage key that doesn't match any anchor should error."""
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "stale.md").write_text(
        "---\nstatus: accepted\ndate: 2026-01-01\n"
        "fixtures: [tests/foo.py]\n"
        "invariant_coverage:\n"
        "  INV-stale-gone:\n    - tests/foo.py\n"
        "---\n# Spec: Stale\n\n## Invariants\n\n",
        encoding="utf-8",
    )
    errors, _ = mod.check(specs, tmp_path)
    assert any("does not match any anchor" in e for e in errors)


def test_unresolved_target_detected(tmp_path: Path) -> None:
    """A spec with invariant_coverage pointing to a nonexistent file should error."""
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "unresolved.md").write_text(
        "---\nstatus: accepted\ndate: 2026-01-01\n"
        "fixtures: [tests/foo.py]\n"
        "invariant_coverage:\n"
        "  INV-unresolved-foo:\n    - tests/nonexistent.py::test_nope\n"
        "---\n# Spec: Unresolved\n\n## Invariants\n\n"
        "<!-- INV-unresolved-foo -->\n1. **Foo.** Must hold.\n",
        encoding="utf-8",
    )
    errors, _ = mod.check(specs, tmp_path)
    assert any("file not found" in e for e in errors)
