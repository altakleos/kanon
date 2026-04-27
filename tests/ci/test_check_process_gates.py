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

import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _REPO_ROOT / "ci" / "check_process_gates.py"
assert _SCRIPT_PATH.is_file(), f"script not found: {_SCRIPT_PATH}"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "check_process_gates", _SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


_M = _load_module()


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def _git(repo: Path, *args: str) -> str:
    """Run git in *repo* with non-interactive identity."""
    env = {
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(repo),
    }
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


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


def _run(repo_path: Path, base_ref: str | None = None) -> dict:
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

def test_docs_only_change_is_ok(tmp_path: Path) -> None:
    """No src/ files changed → ok, both checks skipped."""
    _init_repo(tmp_path)
    (tmp_path / "README.md").write_text("init\n", encoding="utf-8")
    _commit(tmp_path, "chore: init")
    (tmp_path / "docs" / "plans" / "foo.md").write_text("update\n", encoding="utf-8")
    _commit(tmp_path, "docs: update plan")

    report = _run(tmp_path)
    assert report["status"] == "ok"
    assert report["errors"] == []


# ---------------------------------------------------------------------------
# INV-process-gates-plan-co-presence
# ---------------------------------------------------------------------------

def test_src_change_with_plan_status_done(tmp_path: Path) -> None:
    """src/ change + plan with status: done → ok."""
    _init_repo(tmp_path)
    (tmp_path / "src" / "mod.py").write_text("# init\n", encoding="utf-8")
    _commit(tmp_path, "chore: init")
    (tmp_path / "src" / "mod.py").write_text("# changed\n", encoding="utf-8")
    _write_plan(tmp_path, "my-plan", "done")
    _commit(tmp_path, "feat: implement with plan")

    report = _run(tmp_path)
    assert report["status"] == "ok"
    assert report["errors"] == []


def test_src_change_with_plan_status_in_progress(tmp_path: Path) -> None:
    """src/ change + plan with status: in-progress → ok."""
    _init_repo(tmp_path)
    (tmp_path / "src" / "mod.py").write_text("# init\n", encoding="utf-8")
    _commit(tmp_path, "chore: init")
    (tmp_path / "src" / "mod.py").write_text("# changed\n", encoding="utf-8")
    _write_plan(tmp_path, "my-plan", "in-progress")
    _commit(tmp_path, "feat: implement with plan")

    report = _run(tmp_path)
    assert report["status"] == "ok"
    assert report["errors"] == []


def test_src_change_with_no_plan_fails(tmp_path: Path) -> None:
    """src/ change with no plan file → plan co-presence error."""
    _init_repo(tmp_path)
    (tmp_path / "src" / "mod.py").write_text("# init\n", encoding="utf-8")
    _commit(tmp_path, "chore: init")
    (tmp_path / "src" / "mod.py").write_text("# changed\n", encoding="utf-8")
    _commit(tmp_path, "feat: no plan")

    report = _run(tmp_path)
    assert report["status"] == "fail"
    assert len(report["errors"]) == 1
    assert "Plan co-presence violation" in report["errors"][0]


# ---------------------------------------------------------------------------
# INV-process-gates-trivial-override
# ---------------------------------------------------------------------------

def test_src_change_with_trivial_trailer_exempts_plan(tmp_path: Path) -> None:
    """Trivial-change trailer exempts plan co-presence check."""
    _init_repo(tmp_path)
    (tmp_path / "src" / "mod.py").write_text("# init\n", encoding="utf-8")
    _commit(tmp_path, "chore: init")
    (tmp_path / "src" / "mod.py").write_text("# typo fix\n", encoding="utf-8")
    _commit(tmp_path, "fix: typo\n\nTrivial-change: fix typo in comment")

    report = _run(tmp_path)
    assert report["status"] == "ok"
    assert report["errors"] == []


# ---------------------------------------------------------------------------
# INV-process-gates-spec-co-presence
# ---------------------------------------------------------------------------

def test_new_cli_command_with_spec_accepted(tmp_path: Path) -> None:
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

    report = _run(tmp_path)
    assert report["status"] == "ok"
    assert report["errors"] == []


def test_new_cli_command_with_no_spec_fails(tmp_path: Path) -> None:
    """New CLI command with no spec → spec co-presence error."""
    _init_repo(tmp_path)
    (tmp_path / "src" / "cli.py").write_text("# init\n", encoding="utf-8")
    _commit(tmp_path, "chore: init")
    (tmp_path / "src" / "cli.py").write_text(
        "# init\n@cli.command()\ndef new_cmd(): pass\n", encoding="utf-8"
    )
    _write_plan(tmp_path, "my-plan", "done")
    _commit(tmp_path, "feat: add command without spec")

    report = _run(tmp_path)
    assert report["status"] == "fail"
    assert any("Spec co-presence violation" in e for e in report["errors"])


def test_new_cli_command_with_trivial_but_no_spec_still_fails(
    tmp_path: Path,
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

    report = _run(tmp_path)
    assert report["status"] == "fail"
    assert any("Spec co-presence violation" in e for e in report["errors"])
    # Plan check should be exempted by trivial trailer
    assert not any("Plan co-presence" in e for e in report["errors"])


# ---------------------------------------------------------------------------
# INV-process-gates-reference-semantics
# ---------------------------------------------------------------------------

def test_plan_referenced_via_commit_message(tmp_path: Path) -> None:
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

    report = _run(tmp_path)
    assert report["status"] == "ok"
    assert report["errors"] == []


def test_spec_referenced_via_commit_message(tmp_path: Path) -> None:
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

    report = _run(tmp_path)
    assert report["status"] == "ok"
    assert report["errors"] == []


# ---------------------------------------------------------------------------
# INV-process-gates-json-report
# ---------------------------------------------------------------------------

def test_json_report_structure(tmp_path: Path) -> None:
    """Report always has status, errors, and warnings keys."""
    _init_repo(tmp_path)
    (tmp_path / "README.md").write_text("init\n", encoding="utf-8")
    _commit(tmp_path, "chore: init")

    report = _run(tmp_path)
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

def test_pr_mode_with_base_ref(tmp_path: Path) -> None:
    """PR mode (--base-ref) diffs base..HEAD."""
    _init_repo(tmp_path)
    (tmp_path / "src" / "mod.py").write_text("# init\n", encoding="utf-8")
    _commit(tmp_path, "chore: init")
    base = _git(tmp_path, "rev-parse", "HEAD").strip()
    _git(tmp_path, "checkout", "-q", "-b", "feature")
    (tmp_path / "src" / "mod.py").write_text("# changed\n", encoding="utf-8")
    _write_plan(tmp_path, "my-plan", "done")
    _commit(tmp_path, "feat: with plan")

    report = _run(tmp_path, base_ref=base)
    assert report["status"] == "ok"


def test_pr_mode_catches_violation(tmp_path: Path) -> None:
    """PR mode detects missing plan across the range."""
    _init_repo(tmp_path)
    (tmp_path / "src" / "mod.py").write_text("# init\n", encoding="utf-8")
    _commit(tmp_path, "chore: init")
    base = _git(tmp_path, "rev-parse", "HEAD").strip()
    _git(tmp_path, "checkout", "-q", "-b", "feature")
    (tmp_path / "src" / "mod.py").write_text("# changed\n", encoding="utf-8")
    _commit(tmp_path, "feat: no plan")

    report = _run(tmp_path, base_ref=base)
    assert report["status"] == "fail"
    assert any("Plan co-presence" in e for e in report["errors"])


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

def test_cli_exit_zero_on_ok(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
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
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
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
