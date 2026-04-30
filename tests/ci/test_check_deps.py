"""Tests for ci/check_deps.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def mod(load_ci_script):
    return load_ci_script("check_deps.py")


def test_requirements_pinned_ok(mod, tmp_path: Path) -> None:
    req = tmp_path / "requirements.txt"
    req.write_text("click==8.1.7\n")
    assert mod._check_requirements_txt(req) == []


def test_requirements_unpinned_detected(mod, tmp_path: Path) -> None:
    req = tmp_path / "requirements.txt"
    req.write_text("click>=8.0\n")
    findings = mod._check_requirements_txt(req)
    assert len(findings) == 1
    assert findings[0]["rule"] == "unpinned-version"


def test_requirements_bare_name_detected(mod, tmp_path: Path) -> None:
    req = tmp_path / "requirements.txt"
    req.write_text("click\n")
    findings = mod._check_requirements_txt(req)
    assert len(findings) == 1
    assert findings[0]["rule"] == "unpinned-version"


def test_requirements_comments_skipped(mod, tmp_path: Path) -> None:
    req = tmp_path / "requirements.txt"
    req.write_text("# comment\nclick==8.0\n")
    assert mod._check_requirements_txt(req) == []


def test_pyproject_unpinned_detected(mod, tmp_path: Path) -> None:
    toml = tmp_path / "pyproject.toml"
    toml.write_text('[project]\ndependencies = [\n    click = {version = ">=8.0"},\n]\n')
    findings = mod._check_pyproject_toml(toml)
    assert len(findings) >= 1
    assert findings[0]["rule"] == "unpinned-version"


def test_package_json_caret_detected(mod, tmp_path: Path) -> None:
    pj = tmp_path / "package.json"
    pj.write_text(json.dumps({"dependencies": {"express": "^4.18.0"}}))
    findings = mod._check_package_json(pj)
    assert len(findings) == 1
    assert findings[0]["rule"] == "unpinned-version"


def test_package_json_tilde_detected(mod, tmp_path: Path) -> None:
    pj = tmp_path / "package.json"
    pj.write_text(json.dumps({"dependencies": {"express": "~4.18.0"}}))
    findings = mod._check_package_json(pj)
    assert len(findings) == 1
    assert findings[0]["rule"] == "unpinned-version"


def test_duplicate_purpose_detected(mod, tmp_path: Path) -> None:
    req = tmp_path / "requirements.txt"
    req.write_text("requests==2.31.0\nhttpx==0.25.0\n")
    findings = mod._check_duplicates(tmp_path)
    assert len(findings) == 1
    assert findings[0]["rule"] == "duplicate-purpose"
    assert "http" in findings[0]["message"].lower()


def test_no_duplicates_single_lib(mod, tmp_path: Path) -> None:
    req = tmp_path / "requirements.txt"
    req.write_text("requests==2.31.0\n")
    assert mod._check_duplicates(tmp_path) == []


def test_main_exits_zero(
    mod, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    req = tmp_path / "requirements.txt"
    req.write_text("click==8.1.7\n")
    monkeypatch.setattr("sys.argv", ["check_deps", "--root", str(tmp_path)])
    with pytest.raises(SystemExit) as exc_info:
        mod.main()
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    report = json.loads(out)
    assert report["status"] == "ok"


def test_pyproject_requires_python_alone_is_not_a_dependency(mod, tmp_path: Path) -> None:
    """`requires-python = \">=3.10\"` is a PEP 621 Python-version constraint, not a dep.

    Pre-fix, the in_deps state machine treated `[project]` itself as the entry
    boundary, so the value `\">=3.10\"` matched `_PYPROJECT_UNPINNED` and was
    reported. Post-fix, only the body of `<name> = [...]` arrays is scanned.
    """
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "x"\nrequires-python = ">=3.10"\n',
        encoding="utf-8",
    )
    assert mod._check_pyproject_toml(pyproject) == []


def test_pyproject_requires_python_skipped_alongside_dependencies(mod, tmp_path: Path) -> None:
    """`requires-python` outside any array is skipped even when a deps array follows."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\n'
        'name = "x"\n'
        'requires-python = ">=3.10"\n'
        'dependencies = [\n'
        '    "click==8.1.7",\n'
        ']\n',
        encoding="utf-8",
    )
    assert mod._check_pyproject_toml(pyproject) == []


def test_pyproject_dependency_array_still_scanned(mod, tmp_path: Path) -> None:
    """Entries inside `dependencies = [` still match the scanner regex."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\n'
        'requires-python = ">=3.10"\n'
        'dependencies = [\n'
        '    ">=1.0",\n'  # exotic but matches `_PYPROJECT_UNPINNED`
        ']\n',
        encoding="utf-8",
    )
    findings = mod._check_pyproject_toml(pyproject)
    assert len(findings) == 1
    assert "requires-python" not in findings[0]["message"]


def test_pyproject_optional_dependencies_block_scanned(mod, tmp_path: Path) -> None:
    """Arrays inside `[project.optional-dependencies]` are scanned by the same rule."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\n'
        '[project.optional-dependencies]\n'
        'dev = [\n'
        '    ">=7.0",\n'  # exotic but matches `_PYPROJECT_UNPINNED`
        ']\n',
        encoding="utf-8",
    )
    findings = mod._check_pyproject_toml(pyproject)
    assert len(findings) == 1
