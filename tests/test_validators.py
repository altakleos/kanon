"""Tests for the 4 untested validators in kanon_core._validators."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest


# --- deps_hygiene_check ---


class TestDepsHygieneCheck:
    def test_no_manifest_no_warning(self, tmp_path: Path) -> None:
        from kanon_core._validators.deps_hygiene_check import check

        errors: list[str] = []
        warnings: list[str] = []
        check(tmp_path, errors, warnings)
        assert errors == []
        assert warnings == []

    def test_manifest_without_lockfile_warns(self, tmp_path: Path) -> None:
        from kanon_core._validators.deps_hygiene_check import check

        (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        errors: list[str] = []
        warnings: list[str] = []
        check(tmp_path, errors, warnings)
        assert any("no lockfile" in w for w in warnings)
        assert errors == []

    def test_manifest_with_lockfile_no_warning(self, tmp_path: Path) -> None:
        from kanon_core._validators.deps_hygiene_check import check

        (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        (tmp_path / "uv.lock").write_text("", encoding="utf-8")
        errors: list[str] = []
        warnings: list[str] = []
        check(tmp_path, errors, warnings)
        assert not any("no lockfile" in w for w in warnings)

    def test_unpinned_requirements_warns(self, tmp_path: Path) -> None:
        from kanon_core._validators.deps_hygiene_check import check

        (tmp_path / "requirements.txt").write_text(
            "flask\nrequests>=2.0\nclick==8.1.7\n", encoding="utf-8"
        )
        errors: list[str] = []
        warnings: list[str] = []
        check(tmp_path, errors, warnings)
        assert any("unpinned" in w for w in warnings)

    def test_fully_pinned_requirements_no_warning(self, tmp_path: Path) -> None:
        from kanon_core._validators.deps_hygiene_check import check

        (tmp_path / "requirements.txt").write_text(
            "flask==3.0.0\nclick==8.1.7\n", encoding="utf-8"
        )
        # Also need a lockfile to avoid that warning
        (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        (tmp_path / "uv.lock").write_text("", encoding="utf-8")
        errors: list[str] = []
        warnings: list[str] = []
        check(tmp_path, errors, warnings)
        assert not any("unpinned" in w for w in warnings)


# --- orphan_branches ---


class TestOrphanBranches:
    def test_no_worktrees_dir_no_warning(self, tmp_path: Path) -> None:
        from kanon_core._validators.orphan_branches import check

        errors: list[str] = []
        warnings: list[str] = []
        check(str(tmp_path), errors, warnings)
        assert errors == []
        assert warnings == []

    def test_orphan_branch_detected(self, tmp_path: Path) -> None:
        from kanon_core._validators.orphan_branches import check

        # Create .worktrees/ with one active slug
        (tmp_path / ".worktrees" / "active").mkdir(parents=True)

        # Mock git to return branches including an orphan
        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="  wt/active\n  wt/orphan\n", stderr=""
        )
        errors: list[str] = []
        warnings: list[str] = []
        with patch("subprocess.run", return_value=mock_result):
            check(str(tmp_path), errors, warnings)

        assert any("orphan" in w.lower() for w in warnings)
        assert not any("active" in w for w in warnings)

    def test_no_orphans_no_warning(self, tmp_path: Path) -> None:
        from kanon_core._validators.orphan_branches import check

        (tmp_path / ".worktrees" / "feature").mkdir(parents=True)

        mock_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="  wt/feature\n", stderr=""
        )
        errors: list[str] = []
        warnings: list[str] = []
        with patch("subprocess.run", return_value=mock_result):
            check(str(tmp_path), errors, warnings)

        assert warnings == []


# --- test_quality_check ---


class TestTestQualityCheck:
    def test_no_tests_dir_no_warning(self, tmp_path: Path) -> None:
        from kanon_core._validators.test_quality_check import check

        errors: list[str] = []
        warnings: list[str] = []
        check(tmp_path, errors, warnings)
        assert errors == []
        assert warnings == []

    def test_nonspecific_assertions_warns(self, tmp_path: Path) -> None:
        from kanon_core._validators.test_quality_check import check

        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_bad.py").write_text(
            "def test_one():\n    assert result\n\n"
            "def test_two():\n    assert x\n\n"
            "def test_three():\n    assert y is not None\n",
            encoding="utf-8",
        )
        errors: list[str] = []
        warnings: list[str] = []
        check(tmp_path, errors, warnings)
        assert any("non-specific" in w for w in warnings)

    def test_specific_assertions_no_warning(self, tmp_path: Path) -> None:
        from kanon_core._validators.test_quality_check import check

        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_good.py").write_text(
            "def test_one():\n    assert result == 42\n\n"
            "def test_two():\n    assert x > 0\n\n"
            "def test_error():\n    assert err is None\n",
            encoding="utf-8",
        )
        errors: list[str] = []
        warnings: list[str] = []
        check(tmp_path, errors, warnings)
        assert not any("non-specific" in w for w in warnings)

    def test_happy_path_only_warns(self, tmp_path: Path) -> None:
        from kanon_core._validators.test_quality_check import check

        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_happy.py").write_text(
            "def test_create():\n    assert True\n\n"
            "def test_read():\n    assert True\n\n"
            "def test_update():\n    assert True\n",
            encoding="utf-8",
        )
        errors: list[str] = []
        warnings: list[str] = []
        check(tmp_path, errors, warnings)
        assert any("negative" in w.lower() or "error" in w.lower() for w in warnings)


# --- worktree_hygiene ---


class TestWorktreeHygiene:
    def test_no_worktrees_dir_no_warning(self, tmp_path: Path) -> None:
        from kanon_core._validators.worktree_hygiene import check

        errors: list[str] = []
        warnings: list[str] = []
        check(str(tmp_path), errors, warnings)
        assert errors == []
        assert warnings == []

    def test_stale_worktree_warns(self, tmp_path: Path) -> None:
        from kanon_core._validators.worktree_hygiene import check

        (tmp_path / ".worktrees" / "old-feature").mkdir(parents=True)

        # Mock git log to return a timestamp 10 days ago
        import time
        old_ts = str(int(time.time()) - 10 * 86400)
        log_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=old_ts + "\n", stderr=""
        )
        merged_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )

        def mock_run(cmd, **kwargs):
            if "log" in cmd:
                return log_result
            return merged_result

        errors: list[str] = []
        warnings: list[str] = []
        with patch("subprocess.run", side_effect=mock_run):
            check(str(tmp_path), errors, warnings)

        assert any("stale" in w.lower() for w in warnings)

    def test_merged_worktree_warns(self, tmp_path: Path) -> None:
        from kanon_core._validators.worktree_hygiene import check

        (tmp_path / ".worktrees" / "done-feature").mkdir(parents=True)

        import time
        recent_ts = str(int(time.time()) - 3600)  # 1 hour ago (not stale)
        log_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=recent_ts + "\n", stderr=""
        )
        merged_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="  wt/done-feature\n", stderr=""
        )

        def mock_run(cmd, **kwargs):
            if "log" in cmd:
                return log_result
            return merged_result

        errors: list[str] = []
        warnings: list[str] = []
        with patch("subprocess.run", side_effect=mock_run):
            check(str(tmp_path), errors, warnings)

        assert any("merged" in w.lower() for w in warnings)
