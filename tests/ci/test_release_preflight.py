"""Tests for ci/release-preflight.py."""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _REPO_ROOT / "ci" / "release-preflight.py"
assert _SCRIPT_PATH.is_file()


def _load():
    spec = importlib.util.spec_from_file_location("release_preflight", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


mod = _load()


# -- _find_version tests --


def test_find_version_from_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    """_find_version() returns a valid semver-ish string from the real repo."""
    monkeypatch.chdir(_REPO_ROOT)
    version = mod._find_version()
    assert version is not None
    assert re.match(r"\d+\.\d+\.\d+", version)


def test_find_version_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """_find_version() returns None when no src/ directory exists."""
    monkeypatch.chdir(tmp_path)
    assert mod._find_version() is None


def test_find_version_from_init(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """_find_version() extracts version from a synthetic __init__.py."""
    init = tmp_path / "src" / "pkg" / "__init__.py"
    init.parent.mkdir(parents=True)
    init.write_text('__version__ = "1.2.3"\n')
    monkeypatch.chdir(tmp_path)
    assert mod._find_version() == "1.2.3"


# -- changelog logic test --


def test_changelog_entry_present(tmp_path: Path) -> None:
    """The substring check main() uses on CHANGELOG.md finds the version."""
    cl = tmp_path / "CHANGELOG.md"
    cl.write_text("## [1.2.3] - 2026-04-25\n")
    assert "1.2.3" in cl.read_text()


# -- main() integration tests --


def test_main_all_pass(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """main() exits 0 and reports ok=true when everything passes."""
    init = tmp_path / "src" / "pkg" / "__init__.py"
    init.parent.mkdir(parents=True)
    init.write_text('__version__ = "1.2.3"\n')
    (tmp_path / "CHANGELOG.md").write_text("## [1.2.3] - 2026-04-25\n")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["prog", "--tag", "v1.2.3"])

    with patch.object(mod, "_check", return_value=True), pytest.raises(SystemExit) as exc_info:
        mod.main()

    assert exc_info.value.code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    assert all(out["checks"].values())


def test_main_version_mismatch(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """main() exits 1 when __version__ doesn't match the tag."""
    init = tmp_path / "src" / "pkg" / "__init__.py"
    init.parent.mkdir(parents=True)
    init.write_text('__version__ = "1.2.2"\n')
    (tmp_path / "CHANGELOG.md").write_text("## [1.2.3] - 2026-04-25\n")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["prog", "--tag", "v1.2.3"])

    with patch.object(mod, "_check", return_value=True), pytest.raises(SystemExit) as exc_info:
        mod.main()

    assert exc_info.value.code == 1
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False
    assert out["checks"]["version_match"] is False


def test_main_missing_changelog(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """main() exits 1 when CHANGELOG.md is absent."""
    init = tmp_path / "src" / "pkg" / "__init__.py"
    init.parent.mkdir(parents=True)
    init.write_text('__version__ = "1.2.3"\n')
    # No CHANGELOG.md created

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["prog", "--tag", "v1.2.3"])

    with patch.object(mod, "_check", return_value=True), pytest.raises(SystemExit) as exc_info:
        mod.main()

    assert exc_info.value.code == 1
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False
    assert out["checks"]["changelog_entry"] is False
