"""Tests for ci/check_process_gates.py.

Each test sets up a synthetic git repo in tmp_path with the necessary
commits and files, then asserts the gate's verdict.

Coverage:
- docs-only change → ok (INV-process-gates-docs-only-exempt)
- src/ change with plan (status: done) → ok
- src/ change with plan (status: in-progress) → ok
- src/ change with NO plan → error (INV-process-gates-plan-co-presence)
- src/ change with Trivial-change trailer → ok (INV-process-gates-trivial-override)
- new CLI command with spec (status: accepted) → ok (INV-process-gates-spec-co-presence)
- new CLI command with NO spec → error
- new CLI command with Trivial-change but no spec → error (spec never exemptable)
- plan referenced via commit message → ok (INV-process-gates-reference-semantics)
- spec referenced via commit message → ok
- JSON report structure (INV-process-gates-json-report)
- standalone (INV-process-gates-standalone)
- git-aware PR vs push mode (INV-process-gates-git-aware)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import REPO_ROOT, _git


@pytest.fixture(scope="module")
def _M(load_ci_script):
    return load_ci_script("check_process_gates.py")


_SCRIPT_PATH = REPO_ROOT / "ci" / "check_process_gates.py"


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "src").mkdir(parents=True, exist_ok=True)
    (repo / "docs" / "plans").mkdir(parents=True, exist_ok=True)
    (repo / "docs" / "specs").mkdir(parents=True, exist_ok=True)


def _write_plan(repo: Path, slug: str, status: str) -> Path:
    path = repo / "docs" / "plans" / f"{slug}.md"
    path.write_text(
        f"---\nstatus: {status}\n---\n# Plan: {slug}\n",
        encoding="utf-8",
    )
    return path


def _write_spec(repo: Path, slug: str, status: str) -> Path:
    path = repo / "docs" / "specs" / f"{slug}.md"
    path.write_text(
        f"---\nstatus: {status}\n---\n# Spec: {slug}\n",
        encoding="utf-8",
    )
    return path


def _commit(repo: Path, message: str, *paths: str) -> str:
    if paths:
        _git(repo, "add", *paths)
    else:
        _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message, "--allow-empty-message")
    return _git(repo, "rev-parse", "HEAD").strip()


def _run(_M, repo_path: Path, base_ref: str | None = None) -> dict:
    """Call main() and parse the JSON report from stdout."""
    argv = ["--repo", str(repo_path)]
    if base_ref is not None:
        argv.extend(["--base-ref", base_ref])
    import contextlib
    import io

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        _M.main(argv)
    return json.loads(buf.getvalue())


# ---------------------------------------------------------------------------
# INV-process-gates-docs-only-exempt
# ---------------------------------------------------------------------------

def test_docs_only_change_is_ok(_M, tmp_path: Path) -> None:
    """No src/ files changed → ok, both checks skipped."""
    _init_repo(tmp_path)
    (tmp_path / "README.md").write_text("init\n", encoding="utf-8")
    _commit(tmp_path, "chore: init")
    (tmp_path / "docs" / "plans" / "foo.md").write_text("update\n", encoding="utf-8")
    _commit(tmp_path, "docs: update plan")

    report = _run(_M, tmp_path)
    assert report["status"] == "ok"
    assert report["errors"] == []


# ---------------------------------------------------------------------------
# INV-process-gates-plan-co-presence
# ---------------------------------------------------------------------------

def test_src_change_with_plan_status_done(_M, tmp_path: Path) -> None:
    """src/ change + plan with status: done → no error (may warn on same-commit)."""
    _init_repo(tmp_path)
    (tmp_path / "src" / "mod.py").write_text("# init\n", encoding="utf-8")
    _commit(tmp_path, "chore: init")
    (tmp_path / "src" / "mod.py").write_text("# changed\n", encoding="utf-8")
    _write_plan(tmp_path, "my-plan", "done")
    _commit(tmp_path, "feat: implement with plan")

    report = _run(_M, tmp_path)
    assert report["status"] in ("ok", "warn")
    assert report["errors"] == []


def test_src_change_with_plan_status_in_progress(_M, tmp_path: Path) -> None:
    """src/ change + plan with status: in-progress → no error (may warn on same-commit)."""
    _init_repo(tmp_path)
    (tmp_path / "src" / "mod.py").write_text("# init\n", encoding="utf-8")
    _commit(tmp_path, "chore: init")
    (tmp_path / "src" / "mod.py").write_text("# changed\n", encoding="utf-8")
    _write_plan(tmp_path, "my-plan", "in-progress")
    _commit(tmp_path, "feat: implement with plan")

    report = _run(_M, tmp_path)
    assert report["status"] in ("ok", "warn")
    assert report["errors"] == []


def test_src_change_with_no_plan_fails(_M, tmp_path: Path) -> None:
    """src/ change with no plan file → plan co-presence error."""
    _init_repo(tmp_path)
    (tmp_path / "src" / "mod.py").write_text("# init\n", encoding="utf-8")
    _commit(tmp_path, "chore: init")
    (tmp_path / "src" / "mod.py").write_text("# changed\n", encoding="utf-8")
    _commit(tmp_path, "feat: no plan")

    report = _run(_M, tmp_path)
    assert report["status"] == "fail"
    assert len(report["errors"]) == 1
    assert "Plan co-presence violation" in report["errors"][0]


# ---------------------------------------------------------------------------
# INV-process-gates-trivial-override
# ---------------------------------------------------------------------------

def test_src_change_with_trivial_trailer_exempts_plan(_M, tmp_path: Path) -> None:
    """Trivial-change trailer exempts plan co-presence check."""
    _init_repo(tmp_path)
    (tmp_path / "src" / "mod.py").write_text("# init\n", encoding="utf-8")
    _commit(tmp_path, "chore: init")
    (tmp_path / "src" / "mod.py").write_text("# typo fix\n", encoding="utf-8")
    _commit(tmp_path, "fix: typo\n\nTrivial-change: fix typo in comment")

    report = _run(_M, tmp_path)
    assert report["status"] == "ok"
    assert report["errors"] == []


# ---------------------------------------------------------------------------
# INV-process-gates-spec-co-presence
# ---------------------------------------------------------------------------

def test_new_cli_command_with_spec_accepted(_M, tmp_path: Path) -> None:
    """New CLI command + spec with status: accepted → ok."""
    _init_repo(tmp_path)
    (tmp_path / "src" / "cli.py").write_text("# init\n", encoding="utf-8")
    _commit(tmp_path, "chore: init")
    (tmp_path / "src" / "cli.py").write_text(
        "# init\n@cli.command()\ndef new_cmd(): pass\n", encoding="utf-8"
    )
    _write_plan(tmp_path, "my-plan", "done")
    _write_spec(tmp_path, "my-spec", "accepted")
    _commit(tmp_path, "feat: add new command")

    report = _run(_M, tmp_path)
    assert report["status"] in ("ok", "warn")
    assert report["errors"] == []


def test_new_cli_command_with_no_spec_fails(_M, tmp_path: Path) -> None:
    """New CLI command with no spec → spec co-presence error."""
    _init_repo(tmp_path)
    (tmp_path / "src" / "cli.py").write_text("# init\n", encoding="utf-8")
    _commit(tmp_path, "chore: init")
    (tmp_path / "src" / "cli.py").write_text(
        "# init\n@cli.command()\ndef new_cmd(): pass\n", encoding="utf-8"
    )
    _write_plan(tmp_path, "my-plan", "done")
    _commit(tmp_path, "feat: add command without spec")

    report = _run(_M, tmp_path)
    assert report["status"] == "fail"
    assert any("Spec co-presence violation" in e for e in report["errors"])


def test_new_cli_command_with_trivial_but_no_spec_still_fails(
    _M, tmp_path: Path,
) -> None:
    """Trivial-change trailer does NOT exempt spec co-presence check."""
    _init_repo(tmp_path)
    (tmp_path / "src" / "cli.py").write_text("# init\n", encoding="utf-8")
    _commit(tmp_path, "chore: init")
    (tmp_path / "src" / "cli.py").write_text(
        "# init\n@cli.command()\ndef new_cmd(): pass\n", encoding="utf-8"
    )
    _commit(
        tmp_path,
        "feat: add command\n\nTrivial-change: small addition",
    )

    report = _run(_M, tmp_path)
    assert report["status"] == "fail"
    assert any("Spec co-presence violation" in e for e in report["errors"])
    # Plan check should be exempted by trivial trailer
    assert not any("Plan co-presence" in e for e in report["errors"])


@pytest.mark.parametrize(
    "decorator",
    [
        "@main.command()",
        "@aspect.command('list')",
        "@click.group()",
        "@fidelity.command('update')",
        "@main.group()",
    ],
    ids=["main-command", "aspect-subcommand", "click-group", "fidelity-command", "main-group"],
)
def test_named_group_decorators_trigger_spec_gate(
    _M, tmp_path: Path, decorator: str
) -> None:
    """Click decorators on named groups (not just @cli.*) trigger the spec gate."""
    _init_repo(tmp_path)
    (tmp_path / "src" / "cli.py").write_text("# init\n", encoding="utf-8")
    _commit(tmp_path, "chore: init")
    (tmp_path / "src" / "cli.py").write_text(
        f"# init\n{decorator}\ndef new_cmd(): pass\n", encoding="utf-8"
    )
    _write_plan(tmp_path, "my-plan", "done")
    _commit(tmp_path, "feat: add command without spec")

    report = _run(_M, tmp_path)
    assert report["status"] == "fail"
    assert any("Spec co-presence violation" in e for e in report["errors"])


# ---------------------------------------------------------------------------
# Plan/src separation (same-commit warning)
# ---------------------------------------------------------------------------

def test_plan_and_src_in_same_commit_warns(_M, tmp_path: Path) -> None:
    """Plan and src/ in the same commit → warning."""
    _init_repo(tmp_path)
    (tmp_path / "src" / "a.py").write_text("# init\n", encoding="utf-8")
    _commit(tmp_path, "chore: init")
    _write_plan(tmp_path, "my-plan", "done")
    (tmp_path / "src" / "a.py").write_text("# changed\n", encoding="utf-8")
    _commit(tmp_path, "feat: plan and code together")

    report = _run(_M, tmp_path)
    assert report["status"] == "warn"
    assert any("Plan/src same-commit" in w for w in report["warnings"])
    assert report["errors"] == []


def test_plan_and_src_in_same_commit_with_trivial_no_warn(_M, tmp_path: Path) -> None:
    """Trivial-change trailer exempts the separation warning."""
    _init_repo(tmp_path)
    (tmp_path / "src" / "a.py").write_text("# init\n", encoding="utf-8")
    _commit(tmp_path, "chore: init")
    _write_plan(tmp_path, "my-plan", "done")
    (tmp_path / "src" / "a.py").write_text("# changed\n", encoding="utf-8")
    _commit(tmp_path, "fix: trivial\n\nTrivial-change: typo fix")

    report = _run(_M, tmp_path)
    assert not any("Plan/src same-commit" in w for w in report["warnings"])


def test_plan_then_src_in_separate_commits_no_warn(_M, tmp_path: Path) -> None:
    """Plan in one commit, src in another → no warning."""
    _init_repo(tmp_path)
    (tmp_path / "src" / "a.py").write_text("# init\n", encoding="utf-8")
    base = _commit(tmp_path, "chore: init")
    _write_plan(tmp_path, "my-plan", "done")
    _commit(tmp_path, "docs: add plan")
    (tmp_path / "src" / "a.py").write_text("# changed\n", encoding="utf-8")
    _commit(tmp_path, "feat: implement")

    report = _run(_M, tmp_path, base_ref=base)
    assert not any("Plan/src same-commit" in w for w in report["warnings"])


def test_pr_mode_mixed_commit_warns(_M, tmp_path: Path) -> None:
    """PR mode: one clean commit + one mixed commit → warning on the mixed one."""
    _init_repo(tmp_path)
    (tmp_path / "src" / "a.py").write_text("# init\n", encoding="utf-8")
    base = _commit(tmp_path, "chore: init")
    _write_plan(tmp_path, "my-plan", "done")
    _commit(tmp_path, "docs: add plan")
    # Modify plan content so git detects a change in the next commit
    plan = tmp_path / "docs" / "plans" / "my-plan.md"
    plan.write_text(
        "---\nstatus: done\n---\n# Plan: my-plan\n\nUpdated.\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "a.py").write_text("# changed\n", encoding="utf-8")
    _commit(tmp_path, "feat: plan and code in one commit")

    report = _run(_M, tmp_path, base_ref=base)
    assert any("Plan/src same-commit" in w for w in report["warnings"])

    report = _run(_M, tmp_path, base_ref=base)
    assert any("Plan/src same-commit" in w for w in report["warnings"])


# ---------------------------------------------------------------------------
# INV-process-gates-reference-semantics
# ---------------------------------------------------------------------------

def test_plan_referenced_via_commit_message(_M, tmp_path: Path) -> None:
    """Plan: trailer in commit message resolves to file on disk."""
    _init_repo(tmp_path)
    (tmp_path / "src" / "mod.py").write_text("# init\n", encoding="utf-8")
    # Plan file exists but is NOT in the diff of the second commit
    _write_plan(tmp_path, "existing-plan", "accepted")
    _commit(tmp_path, "chore: init with plan")
    (tmp_path / "src" / "mod.py").write_text("# changed\n", encoding="utf-8")
    _commit(
        tmp_path,
        "feat: implement\n\nPlan: docs/plans/existing-plan.md",
    )

    report = _run(_M, tmp_path)
    assert report["status"] == "ok"
    assert report["errors"] == []


def test_spec_referenced_via_commit_message(_M, tmp_path: Path) -> None:
    """Spec: trailer in commit message resolves to file on disk."""
    _init_repo(tmp_path)
    (tmp_path / "src" / "cli.py").write_text("# init\n", encoding="utf-8")
    _write_spec(tmp_path, "existing-spec", "provisional")
    _commit(tmp_path, "chore: init")
    (tmp_path / "src" / "cli.py").write_text(
        "# init\n@cli.command()\ndef new_cmd(): pass\n", encoding="utf-8"
    )
    _write_plan(tmp_path, "my-plan", "done")
    _commit(
        tmp_path,
        "feat: add command\n\nSpec: docs/specs/existing-spec.md",
    )

    report = _run(_M, tmp_path)
    assert report["status"] in ("ok", "warn")
    assert report["errors"] == []


# ---------------------------------------------------------------------------
# INV-process-gates-json-report
# ---------------------------------------------------------------------------

def test_json_report_structure(_M, tmp_path: Path) -> None:
    """Report always has status, errors, and warnings keys."""
    _init_repo(tmp_path)
    (tmp_path / "README.md").write_text("init\n", encoding="utf-8")
    _commit(tmp_path, "chore: init")

    report = _run(_M, tmp_path)
    assert "status" in report
    assert "errors" in report
    assert "warnings" in report
    assert isinstance(report["errors"], list)
    assert isinstance(report["warnings"], list)


# ---------------------------------------------------------------------------
# INV-process-gates-standalone
# ---------------------------------------------------------------------------

def test_no_kanon_imports() -> None:
    """The script must have zero imports from kanon.*."""
    text = _SCRIPT_PATH.read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        assert "import kanon" not in stripped, (
            f"Found kanon import: {stripped}"
        )
        assert "from kanon" not in stripped, (
            f"Found kanon import: {stripped}"
        )


# ---------------------------------------------------------------------------
# INV-process-gates-git-aware (PR mode vs push mode)
# ---------------------------------------------------------------------------

def test_pr_mode_with_base_ref(_M, tmp_path: Path) -> None:
    """PR mode (--base-ref) diffs base..HEAD."""
    _init_repo(tmp_path)
    (tmp_path / "src" / "mod.py").write_text("# init\n", encoding="utf-8")
    _commit(tmp_path, "chore: init")
    base = _git(tmp_path, "rev-parse", "HEAD").strip()
    _git(tmp_path, "checkout", "-q", "-b", "feature")
    (tmp_path / "src" / "mod.py").write_text("# changed\n", encoding="utf-8")
    _write_plan(tmp_path, "my-plan", "done")
    _commit(tmp_path, "feat: with plan")

    report = _run(_M, tmp_path, base_ref=base)
    assert report["status"] in ("ok", "warn")


def test_pr_mode_catches_violation(_M, tmp_path: Path) -> None:
    """PR mode detects missing plan across the range."""
    _init_repo(tmp_path)
    (tmp_path / "src" / "mod.py").write_text("# init\n", encoding="utf-8")
    _commit(tmp_path, "chore: init")
    base = _git(tmp_path, "rev-parse", "HEAD").strip()
    _git(tmp_path, "checkout", "-q", "-b", "feature")
    (tmp_path / "src" / "mod.py").write_text("# changed\n", encoding="utf-8")
    _commit(tmp_path, "feat: no plan")

    report = _run(_M, tmp_path, base_ref=base)
    assert report["status"] == "fail"
    assert any("Plan co-presence" in e for e in report["errors"])


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

def test_cli_exit_zero_on_ok(
    _M, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _init_repo(tmp_path)
    (tmp_path / "README.md").write_text("init\n", encoding="utf-8")
    _commit(tmp_path, "chore: init")

    rc = _M.main(["--repo", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    report = json.loads(out)
    assert report["status"] == "ok"


def test_cli_exit_one_on_fail(
    _M, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _init_repo(tmp_path)
    (tmp_path / "src" / "mod.py").write_text("# init\n", encoding="utf-8")
    _commit(tmp_path, "chore: init")
    (tmp_path / "src" / "mod.py").write_text("# changed\n", encoding="utf-8")
    _commit(tmp_path, "feat: no plan")

    rc = _M.main(["--repo", str(tmp_path)])
    assert rc == 1
    out = capsys.readouterr().out
    report = json.loads(out)
    assert report["status"] == "fail"
