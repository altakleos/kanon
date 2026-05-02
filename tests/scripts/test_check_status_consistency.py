"""Tests for scripts/check_status_consistency.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def mod(load_ci_script):
    return load_ci_script("check_status_consistency.py")


def test_real_repo_passes(mod, repo_root) -> None:
    """The kanon repo itself must have no status consistency errors."""
    errors, warnings = mod.check(repo_root)
    assert errors == [], "status consistency errors:\n  " + "\n  ".join(errors)


def test_main_exits_zero_on_ok(mod, repo_root, capsys: pytest.CaptureFixture[str]) -> None:
    rc = mod.main(["--root", str(repo_root)])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["status"] == "ok"


def test_design_spec_drift_detected(mod, tmp_path: Path) -> None:
    """Draft design doc whose implementing spec is accepted triggers warning."""
    design_dir = tmp_path / "docs" / "design"
    design_dir.mkdir(parents=True)
    specs_dir = tmp_path / "docs" / "specs"
    specs_dir.mkdir(parents=True)
    (specs_dir / "foo.md").write_text(
        "---\nstatus: accepted\n---\n# Spec: Foo\n", encoding="utf-8"
    )
    (design_dir / "foo.md").write_text(
        "---\nstatus: draft\nimplements: docs/specs/foo.md\n---\n# Design: Foo\n",
        encoding="utf-8",
    )
    warnings = mod.check_design_spec_drift(tmp_path)
    assert len(warnings) == 1
    assert "draft" in warnings[0]
    assert "accepted" in warnings[0]


def test_design_accepted_no_warning(mod, tmp_path: Path) -> None:
    """Accepted design doc produces no warning even if spec is accepted."""
    design_dir = tmp_path / "docs" / "design"
    design_dir.mkdir(parents=True)
    specs_dir = tmp_path / "docs" / "specs"
    specs_dir.mkdir(parents=True)
    (specs_dir / "foo.md").write_text(
        "---\nstatus: accepted\n---\n# Spec\n", encoding="utf-8"
    )
    (design_dir / "foo.md").write_text(
        "---\nstatus: accepted\nimplements: docs/specs/foo.md\n---\n# Design\n",
        encoding="utf-8",
    )
    warnings = mod.check_design_spec_drift(tmp_path)
    assert warnings == []


def test_plan_planned_with_checked_tasks(mod, tmp_path: Path) -> None:
    """Plan with status:planned but checked tasks triggers warning."""
    plans_dir = tmp_path / "docs" / "plans"
    plans_dir.mkdir(parents=True)
    (plans_dir / "foo.md").write_text(
        "---\nstatus: planned\n---\n# Plan\n- [x] T1: done\n- [ ] T2: todo\n",
        encoding="utf-8",
    )
    warnings = mod.check_plan_status_drift(tmp_path)
    assert len(warnings) == 1
    assert "planned" in warnings[0]
    assert "checked" in warnings[0]


def test_plan_done_all_checked_no_warning(mod, tmp_path: Path) -> None:
    """Plan with status:done and all tasks checked produces no warning."""
    plans_dir = tmp_path / "docs" / "plans"
    plans_dir.mkdir(parents=True)
    (plans_dir / "foo.md").write_text(
        "---\nstatus: done\n---\n# Plan\n- [x] T1\n- [x] T2\n",
        encoding="utf-8",
    )
    warnings = mod.check_plan_status_drift(tmp_path)
    assert warnings == []


def test_plan_done_with_mixed_checkboxes_warns(mod, tmp_path: Path) -> None:
    """Plan done with ANY unchecked task triggers warning. The rule no longer
    requires `checked == 0` — a mix of [x] and [ ] is the same kind of
    contradiction as all-unchecked: a `done` plan claims all work shipped,
    `- [ ]` says otherwise. Use `- [~]` with NOTE to defer.
    """
    plans_dir = tmp_path / "docs" / "plans"
    plans_dir.mkdir(parents=True)
    (plans_dir / "foo.md").write_text(
        "---\nstatus: done\n---\n# Plan\n- [x] T1\n- [ ] T2\n",
        encoding="utf-8",
    )
    warnings = mod.check_plan_status_drift(tmp_path)
    assert len(warnings) == 1
    assert "done" in warnings[0]
    assert "unchecked" in warnings[0]


def test_plan_done_zero_checked_all_unchecked_warns(mod, tmp_path: Path) -> None:
    """Plan done with 0 checked and N unchecked is suspicious."""
    plans_dir = tmp_path / "docs" / "plans"
    plans_dir.mkdir(parents=True)
    (plans_dir / "foo.md").write_text(
        "---\nstatus: done\n---\n# Plan\n- [ ] T1\n- [ ] T2\n",
        encoding="utf-8",
    )
    warnings = mod.check_plan_status_drift(tmp_path)
    assert len(warnings) == 1
    assert "done" in warnings[0]
    assert "unchecked" in warnings[0]


def test_plan_done_with_deferred_items_no_warning(mod, tmp_path: Path) -> None:
    """`- [~]` deferred items don't count as unchecked. A plan with all
    [x] and [~] (and zero [ ]) is internally consistent under the
    project's checkbox convention.
    """
    plans_dir = tmp_path / "docs" / "plans"
    plans_dir.mkdir(parents=True)
    (plans_dir / "foo.md").write_text(
        "---\nstatus: done\n---\n# Plan\n- [x] T1\n- [~] T2 — DEFERRED. NOTE: out of scope.\n",
        encoding="utf-8",
    )
    warnings = mod.check_plan_status_drift(tmp_path)
    assert warnings == []
