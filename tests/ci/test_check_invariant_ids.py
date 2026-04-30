"""Tests for ci/check_invariant_ids.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def mod(load_ci_script):
    return load_ci_script("check_invariant_ids.py")


def test_real_repo_passes(mod, repo_root) -> None:
    """The kanon repo itself must pass invariant-id checks."""
    errors, _warnings = mod.check(
        repo_root / "docs" / "specs",
        repo_root / "docs",
    )
    assert errors == [], "check_invariant_ids failed:\n  " + "\n  ".join(errors)


def test_main_exits_zero_on_ok(mod, repo_root, capsys: pytest.CaptureFixture[str]) -> None:
    rc = mod.main([
        "--specs", str(repo_root / "docs" / "specs"),
        "--docs", str(repo_root / "docs"),
    ])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["status"] == "ok"


def test_missing_anchor_detected(mod, tmp_path: Path) -> None:
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


def test_duplicate_anchor_detected(mod, tmp_path: Path) -> None:
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
