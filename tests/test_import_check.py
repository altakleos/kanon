"""Tests for kanon._validators.test_import_check."""
from __future__ import annotations

from pathlib import Path

from kanon_core._validators.test_import_check import check

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_real_repo_passes() -> None:
    """The kanon repo itself must have no orphaned CI test references."""
    errors: list[str] = []
    warnings: list[str] = []
    check(_REPO_ROOT, errors, warnings)
    assert errors == [], "test-import-check failed:\n  " + "\n  ".join(errors)


def test_orphan_detected(tmp_path: Path) -> None:
    """A test file referencing a missing CI script should error."""
    tests_ci = tmp_path / "tests" / "scripts"
    tests_ci.mkdir(parents=True)
    (tests_ci / "test_check_gone.py").write_text(
        'from pathlib import Path\n'
        '_REPO_ROOT = Path(__file__).resolve().parents[2]\n'
        '_SCRIPT_PATH = _REPO_ROOT / "scripts" / "check_gone.py"\n',
        encoding="utf-8",
    )
    (tmp_path / "scripts").mkdir()
    errors: list[str] = []
    warnings: list[str] = []
    check(tmp_path, errors, warnings)
    assert len(errors) == 1
    assert "check_gone.py" in errors[0]
    assert "does not exist" in errors[0]


def test_valid_reference_passes(tmp_path: Path) -> None:
    """A test file referencing an existing CI script should not error."""
    tests_ci = tmp_path / "tests" / "scripts"
    tests_ci.mkdir(parents=True)
    (tests_ci / "test_check_ok.py").write_text(
        'from pathlib import Path\n'
        '_REPO_ROOT = Path(__file__).resolve().parents[2]\n'
        '_SCRIPT_PATH = _REPO_ROOT / "scripts" / "check_ok.py"\n',
        encoding="utf-8",
    )
    ci_dir = tmp_path / "scripts"
    ci_dir.mkdir()
    (ci_dir / "check_ok.py").write_text("# ok", encoding="utf-8")
    errors: list[str] = []
    warnings: list[str] = []
    check(tmp_path, errors, warnings)
    assert errors == []


def test_skips_missing_tests_ci(tmp_path: Path) -> None:
    """Validator should silently return when tests/scripts/ doesn't exist."""
    errors: list[str] = []
    warnings: list[str] = []
    check(tmp_path, errors, warnings)
    assert errors == []


def test_validator_path_variant(tmp_path: Path) -> None:
    """The _VALIDATOR_PATH variant should also be detected."""
    tests_ci = tmp_path / "tests" / "scripts"
    tests_ci.mkdir(parents=True)
    (tests_ci / "test_check_missing.py").write_text(
        'from pathlib import Path\n'
        '_REPO_ROOT = Path(__file__).resolve().parents[2]\n'
        '_VALIDATOR_PATH = _REPO_ROOT / "scripts" / "check_missing.py"\n',
        encoding="utf-8",
    )
    (tmp_path / "scripts").mkdir()
    errors: list[str] = []
    warnings: list[str] = []
    check(tmp_path, errors, warnings)
    assert len(errors) == 1
    assert "check_missing.py" in errors[0]
