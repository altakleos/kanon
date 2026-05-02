"""Tests for scripts/check_commit_messages.py.

Each test creates a synthetic git repo in tmp_path with crafted commits,
then asserts the linter's verdict.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import REPO_ROOT, _git


@pytest.fixture(scope="module")
def _M(load_ci_script):
    return load_ci_script("check_commit_messages.py")


_SCRIPT_PATH = REPO_ROOT / "scripts" / "check_commit_messages.py"


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.com")
    (repo / "README.md").write_text("# test\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "chore: initial commit")
    return repo


def _commit(repo: Path, msg: str, filename: str = "f.txt") -> str:
    f = repo / filename
    f.write_text(f"{msg}\n", encoding="utf-8")
    _git(repo, "add", filename)
    _git(repo, "commit", "-m", msg)
    return _git(repo, "rev-parse", "HEAD").strip()


def _run(_M, repo: Path, base_ref: str | None = None) -> dict:
    import contextlib
    import io

    argv = ["--repo", str(repo)]
    if base_ref is not None:
        argv.extend(["--base-ref", base_ref])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        _M.main(argv)
    return json.loads(buf.getvalue())


# ---------------------------------------------------------------------------
# Valid messages
# ---------------------------------------------------------------------------


def test_valid_conventional_commit(_M, tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _commit(repo, "feat: add new feature")
    report = _run(_M, repo)
    assert report["status"] == "ok"
    assert report["warnings"] == []


def test_all_valid_types(_M, tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD").strip()
    for t in ("feat", "fix", "docs", "refactor", "test", "chore"):
        _commit(repo, f"{t}: valid message", f"{t}.txt")
    report = _run(_M, repo, base_ref=base)
    assert report["status"] == "ok"
    assert report["warnings"] == []


def test_scoped_type_is_valid(_M, tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _commit(repo, "feat(cli): add new flag")
    report = _run(_M, repo)
    assert report["status"] == "ok"


def test_breaking_change_bang_is_valid(_M, tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _commit(repo, "feat!: breaking change")
    report = _run(_M, repo)
    assert report["status"] == "ok"


def test_merge_commit_is_skipped(_M, tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _commit(repo, "Merge branch 'feature' into main")
    report = _run(_M, repo)
    assert report["status"] == "ok"
    assert report["warnings"] == []


# ---------------------------------------------------------------------------
# Invalid messages
# ---------------------------------------------------------------------------


def test_no_type_prefix_warns(_M, tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _commit(repo, "added a new feature")
    report = _run(_M, repo)
    assert report["status"] == "warn"
    assert len(report["warnings"]) == 1
    assert "not Conventional Commits format" in report["warnings"][0]


def test_unknown_type_warns(_M, tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _commit(repo, "yolo: did something")
    report = _run(_M, repo)
    assert report["status"] == "warn"
    assert len(report["warnings"]) == 1
    assert "unknown type 'yolo'" in report["warnings"][0]


def test_missing_space_after_colon_warns(_M, tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _commit(repo, "feat:no space")
    report = _run(_M, repo)
    assert report["status"] == "warn"
    assert len(report["warnings"]) == 1


# ---------------------------------------------------------------------------
# Soft check — always exit 0
# ---------------------------------------------------------------------------


def test_always_exits_zero_even_with_warnings(_M, tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _commit(repo, "bad message no prefix")
    report = _run(_M, repo)
    assert report["status"] == "warn"
    assert report["errors"] == []


# ---------------------------------------------------------------------------
# PR mode
# ---------------------------------------------------------------------------


def test_pr_mode_checks_range(_M, tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    base = _git(repo, "rev-parse", "HEAD").strip()
    _commit(repo, "no prefix at all", "a.txt")
    _commit(repo, "feat: valid one", "b.txt")
    report = _run(_M, repo, base_ref=base)
    assert report["status"] == "warn"
    assert len(report["warnings"]) == 1
    assert "no prefix at all" in report["warnings"][0]


# ---------------------------------------------------------------------------
# JSON structure
# ---------------------------------------------------------------------------


def test_report_has_required_keys(_M, tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _commit(repo, "feat: something")
    report = _run(_M, repo)
    assert set(report.keys()) == {"status", "errors", "warnings"}
    assert isinstance(report["errors"], list)
    assert isinstance(report["warnings"], list)


# ---------------------------------------------------------------------------
# Standalone
# ---------------------------------------------------------------------------


def test_no_kanon_imports() -> None:
    source = _SCRIPT_PATH.read_text(encoding="utf-8")
    assert "from kanon" not in source
    assert "import kanon" not in source
