"""Tests for kanon CLI: fidelity lock commands."""

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml
from click.testing import CliRunner

from kanon.cli import main

# --- fidelity lock tests ---


def test_fidelity_update_creates_lock(tmp_path: Path) -> None:
    """init tier 2, create a spec, run fidelity update, assert lock exists."""
    runner = CliRunner()
    target = tmp_path / "proj"
    runner.invoke(main, ["init", str(target), "--tier", "2"])
    spec = target / "docs" / "specs" / "example.md"
    spec.write_text("---\nstatus: accepted\ndate: 2026-01-01\n---\n# Spec: Example\n", encoding="utf-8")
    result = runner.invoke(main, ["fidelity", "update", str(target)])
    assert result.exit_code == 0, result.output
    lock = target / ".kanon" / "fidelity.lock"
    assert lock.is_file()
    data = yaml.safe_load(lock.read_text(encoding="utf-8"))
    assert data["lock_version"] == 1
    assert "example" in data["entries"]
    assert data["entries"]["example"]["spec_sha"].startswith("sha256:")



def test_fidelity_update_idempotent(tmp_path: Path) -> None:
    """Running fidelity update twice produces identical output (except locked_at)."""
    runner = CliRunner()
    target = tmp_path / "proj"
    runner.invoke(main, ["init", str(target), "--tier", "2"])
    spec = target / "docs" / "specs" / "example.md"
    spec.write_text("---\nstatus: accepted\ndate: 2026-01-01\n---\n# Spec: Example\n", encoding="utf-8")
    runner.invoke(main, ["fidelity", "update", str(target)])
    lock1 = yaml.safe_load((target / ".kanon" / "fidelity.lock").read_text(encoding="utf-8"))
    runner.invoke(main, ["fidelity", "update", str(target)])
    lock2 = yaml.safe_load((target / ".kanon" / "fidelity.lock").read_text(encoding="utf-8"))
    assert lock1["entries"]["example"]["spec_sha"] == lock2["entries"]["example"]["spec_sha"]



def test_fidelity_lock_includes_fixture_shas(tmp_path: Path) -> None:
    """Spec with invariant_coverage produces fixture_shas in lock."""
    runner = CliRunner()
    target = tmp_path / "proj"
    runner.invoke(main, ["init", str(target), "--tier", "2"])
    # Create a test file
    test_file = target / "tests" / "test_example.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("def test_one(): pass\n", encoding="utf-8")
    # Create a spec with invariant_coverage pointing to the test file
    spec = target / "docs" / "specs" / "example.md"
    spec.write_text(
        "---\nstatus: accepted\ndate: 2026-01-01\n"
        "invariant_coverage:\n"
        "  INV-example-one:\n"
        "    - tests/test_example.py::test_one\n"
        "---\n# Spec: Example\n",
        encoding="utf-8",
    )
    result = runner.invoke(main, ["fidelity", "update", str(target)])
    assert result.exit_code == 0, result.output
    lock = target / ".kanon" / "fidelity.lock"
    data = yaml.safe_load(lock.read_text(encoding="utf-8"))
    entry = data["entries"]["example"]
    assert "fixture_shas" in entry
    assert "tests/test_example.py" in entry["fixture_shas"]
    expected_sha = "sha256:" + hashlib.sha256(test_file.read_bytes()).hexdigest()
    assert entry["fixture_shas"]["tests/test_example.py"] == expected_sha
