"""Tests for ci/check_test_quality.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def mod(load_ci_script):
    return load_ci_script("check_test_quality.py")


def test_real_repo_passes(mod, repo_root) -> None:
    """The kanon repo's own tests must have zero quality errors."""
    test_files = mod._find_test_files(repo_root)
    all_errors: list[str] = []
    for tf in test_files:
        errs, _ = mod._check_file(tf)
        all_errors.extend(errs)
    assert all_errors == [], "check_test_quality errors:\n  " + "\n  ".join(all_errors)


def test_trivial_pass_body_detected(mod, tmp_path: Path) -> None:
    f = tmp_path / "test_example.py"
    f.write_text("def test_nothing():\n    pass\n", encoding="utf-8")
    errors, _ = mod._check_file(f)
    assert errors, "expected errors for trivial pass body"
    assert any("trivial" in e for e in errors)


def test_trivial_assert_true_detected(mod, tmp_path: Path) -> None:
    f = tmp_path / "test_example.py"
    f.write_text("def test_nothing():\n    assert True\n", encoding="utf-8")
    errors, _ = mod._check_file(f)
    assert errors, "expected errors for trivial assert True body"


def test_real_test_passes(mod, tmp_path: Path) -> None:
    f = tmp_path / "test_example.py"
    f.write_text("def test_addition():\n    assert 1 + 1 == 2\n", encoding="utf-8")
    errors, _ = mod._check_file(f)
    assert errors == []


def test_no_test_functions_warns(mod, tmp_path: Path) -> None:
    f = tmp_path / "test_example.py"
    f.write_text("x = 1\n", encoding="utf-8")
    _, warnings = mod._check_file(f)
    assert warnings, "expected warnings for file with no test functions"
    assert any("zero test functions" in w for w in warnings)


def test_find_test_files_patterns(mod, tmp_path: Path) -> None:
    (tmp_path / "test_foo.py").write_text("", encoding="utf-8")
    (tmp_path / "bar.py").write_text("", encoding="utf-8")
    found = mod._find_test_files(tmp_path)
    names = [p.name for p in found]
    assert "test_foo.py" in names
    assert "bar.py" not in names


def test_main_exits_zero_on_clean(
    mod, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "test_ok.py").write_text(
        "def test_real():\n    assert 1 + 1 == 2\n", encoding="utf-8",
    )
    monkeypatch.setattr("sys.argv", ["check_test_quality", "--root", str(tmp_path)])
    with pytest.raises(SystemExit) as exc_info:
        mod.main()
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    report = json.loads(out)
    assert report["status"] == "ok"
    assert report["errors"] == []


def test_main_exits_one_on_trivial(
    mod, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "test_bad.py").write_text(
        "def test_nothing():\n    pass\n", encoding="utf-8",
    )
    monkeypatch.setattr("sys.argv", ["check_test_quality", "--root", str(tmp_path)])
    with pytest.raises(SystemExit, match="1"):
        mod.main()


def test_skip_dirs_excludes_venv_and_friends(mod, tmp_path: Path) -> None:
    """Test files inside `.venv/`, `node_modules/`, etc. are not collected."""
    real = tmp_path / "tests" / "test_real.py"
    real.parent.mkdir(parents=True)
    real.write_text(
        "def test_one():\n    assert 1 == 1\n", encoding="utf-8",
    )
    venv_test = tmp_path / ".venv" / "lib" / "python3.11" / "site-packages" / "mypy" / "test_skip.py"
    venv_test.parent.mkdir(parents=True)
    venv_test.write_text("# would otherwise warn: zero test functions\n", encoding="utf-8")
    node_test = tmp_path / "node_modules" / "foo" / "test_skip.py"
    node_test.parent.mkdir(parents=True)
    node_test.write_text("# would otherwise warn: zero test functions\n", encoding="utf-8")

    found = mod._find_test_files(tmp_path)
    found_relative = {p.relative_to(tmp_path).as_posix() for p in found}
    assert found_relative == {"tests/test_real.py"}
