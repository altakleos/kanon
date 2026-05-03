"""Tests for kanon._validators.index_consistency."""
from __future__ import annotations

from pathlib import Path

from kanon_core._validators.index_consistency import check

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_real_repo_passes() -> None:
    """The kanon repo itself must have no duplicate index entries."""
    errors: list[str] = []
    warnings: list[str] = []
    check(_REPO_ROOT, errors, warnings)
    assert errors == [], "index-consistency failed:\n  " + "\n  ".join(errors)


def test_duplicate_detected(tmp_path: Path) -> None:
    """A README with duplicate link targets should error."""
    specs = tmp_path / "docs" / "specs"
    specs.mkdir(parents=True)
    (specs / "README.md").write_text(
        "# Specs\n\n"
        "| Spec | Status |\n"
        "| --- | --- |\n"
        "| [Foo](foo.md) | accepted |\n"
        "| [Bar](bar.md) | accepted |\n"
        "| [Foo Again](foo.md) | accepted |\n",
        encoding="utf-8",
    )
    errors: list[str] = []
    warnings: list[str] = []
    check(tmp_path, errors, warnings)
    assert len(errors) == 1
    assert "foo.md" in errors[0]
    assert "duplicate" in errors[0]


def test_no_false_positive_on_clean_index(tmp_path: Path) -> None:
    """A README with unique entries should pass."""
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    (plans / "README.md").write_text(
        "# Plans\n\n"
        "| Plan | Status |\n"
        "| --- | --- |\n"
        "| [Alpha](alpha.md) | done |\n"
        "| [Beta](beta.md) | done |\n",
        encoding="utf-8",
    )
    errors: list[str] = []
    warnings: list[str] = []
    check(tmp_path, errors, warnings)
    assert errors == []


def test_skips_missing_dirs(tmp_path: Path) -> None:
    """Validator should not error when docs/ subdirs don't exist."""
    (tmp_path / "docs").mkdir()
    errors: list[str] = []
    warnings: list[str] = []
    check(tmp_path, errors, warnings)
    assert errors == []


def test_skips_code_blocks(tmp_path: Path) -> None:
    """Links inside code blocks should be ignored."""
    decisions = tmp_path / "docs" / "decisions"
    decisions.mkdir(parents=True)
    (decisions / "README.md").write_text(
        "# Decisions\n\n"
        "| Decision | Status |\n"
        "| --- | --- |\n"
        "| [Real](real.md) | accepted |\n"
        "\n```\n"
        "| [Real](real.md) | accepted |\n"
        "```\n",
        encoding="utf-8",
    )
    errors: list[str] = []
    warnings: list[str] = []
    check(tmp_path, errors, warnings)
    assert errors == []


def test_no_docs_dir(tmp_path: Path) -> None:
    """Validator should silently return when docs/ doesn't exist."""
    errors: list[str] = []
    warnings: list[str] = []
    check(tmp_path, errors, warnings)
    assert errors == []
