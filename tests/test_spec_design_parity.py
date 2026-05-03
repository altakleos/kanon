"""Tests for the spec-design parity validator."""
from __future__ import annotations

from pathlib import Path

from kanon_core._validators.spec_design_parity import check


def _write_spec(specs_dir: Path, name: str, status: str = "accepted", extra_fm: str = "") -> None:
    (specs_dir / f"{name}.md").write_text(
        f"---\nstatus: {status}\n{extra_fm}---\n# Spec: {name}\n",
        encoding="utf-8",
    )


def test_accepted_spec_with_design_doc_no_warning(tmp_path: Path) -> None:
    (tmp_path / "docs" / "specs").mkdir(parents=True)
    (tmp_path / "docs" / "design").mkdir(parents=True)
    _write_spec(tmp_path / "docs" / "specs", "foo")
    (tmp_path / "docs" / "design" / "foo.md").write_text("# Design: foo\n")
    errors: list[str] = []
    warnings: list[str] = []
    check(tmp_path, errors, warnings)
    assert not errors
    assert not warnings


def test_accepted_spec_without_design_doc_warns(tmp_path: Path) -> None:
    (tmp_path / "docs" / "specs").mkdir(parents=True)
    _write_spec(tmp_path / "docs" / "specs", "foo")
    errors: list[str] = []
    warnings: list[str] = []
    check(tmp_path, errors, warnings)
    assert not errors
    assert any("foo.md" in w for w in warnings)


def test_draft_spec_ignored(tmp_path: Path) -> None:
    (tmp_path / "docs" / "specs").mkdir(parents=True)
    _write_spec(tmp_path / "docs" / "specs", "foo", status="draft")
    errors: list[str] = []
    warnings: list[str] = []
    check(tmp_path, errors, warnings)
    assert not warnings


def test_design_skip_in_frontmatter_suppresses_warning(tmp_path: Path) -> None:
    (tmp_path / "docs" / "specs").mkdir(parents=True)
    _write_spec(tmp_path / "docs" / "specs", "foo", extra_fm="design: skip\n")
    errors: list[str] = []
    warnings: list[str] = []
    check(tmp_path, errors, warnings)
    assert not warnings


def test_design_adr_ref_in_frontmatter_suppresses_warning(tmp_path: Path) -> None:
    (tmp_path / "docs" / "specs").mkdir(parents=True)
    _write_spec(tmp_path / "docs" / "specs", "foo", extra_fm='design: "Follows ADR-0006"\n')
    errors: list[str] = []
    warnings: list[str] = []
    check(tmp_path, errors, warnings)
    assert not warnings


def test_no_specs_dir_no_crash(tmp_path: Path) -> None:
    errors: list[str] = []
    warnings: list[str] = []
    check(tmp_path, errors, warnings)
    assert not errors
    assert not warnings


# --- Coverage gap tests: defensive branches ---


def test_template_spec_skipped(tmp_path: Path) -> None:
    """_template.md is skipped even with accepted status."""
    (tmp_path / "docs" / "specs").mkdir(parents=True)
    (tmp_path / "docs" / "specs" / "_template.md").write_text(
        "---\nstatus: accepted\n---\n# Template\n", encoding="utf-8"
    )
    errors: list[str] = []
    warnings: list[str] = []
    check(tmp_path, errors, warnings)
    assert not errors
    assert not warnings


def test_unreadable_spec_skipped(tmp_path: Path) -> None:
    """Unreadable spec file is silently skipped."""
    import os
    import sys
    if sys.platform == "win32":
        return
    (tmp_path / "docs" / "specs").mkdir(parents=True)
    p = tmp_path / "docs" / "specs" / "bad.md"
    p.write_text("---\nstatus: accepted\n---\n", encoding="utf-8")
    try:
        os.chmod(str(p), 0o000)
        errors: list[str] = []
        warnings: list[str] = []
        check(tmp_path, errors, warnings)
        assert not errors
        assert not warnings
    finally:
        os.chmod(str(p), 0o644)


def test_spec_without_frontmatter_skipped(tmp_path: Path) -> None:
    """Specs without valid frontmatter delimiters are skipped."""
    (tmp_path / "docs" / "specs").mkdir(parents=True)
    # No opening ---
    (tmp_path / "docs" / "specs" / "nofm.md").write_text(
        "# No frontmatter\n", encoding="utf-8"
    )
    # Opening --- but no closing ---
    (tmp_path / "docs" / "specs" / "noclose.md").write_text(
        "---\nstatus: accepted\n# No closing delimiter\n", encoding="utf-8"
    )
    errors: list[str] = []
    warnings: list[str] = []
    check(tmp_path, errors, warnings)
    assert not errors
    assert not warnings


def test_spec_with_invalid_yaml_skipped(tmp_path: Path) -> None:
    """Specs with invalid YAML or non-dict frontmatter are skipped."""
    (tmp_path / "docs" / "specs").mkdir(parents=True)
    # Invalid YAML
    (tmp_path / "docs" / "specs" / "badyaml.md").write_text(
        "---\n: [invalid yaml\n---\n", encoding="utf-8"
    )
    # Non-dict frontmatter (bare string)
    (tmp_path / "docs" / "specs" / "barestr.md").write_text(
        "---\njust a string\n---\n", encoding="utf-8"
    )
    errors: list[str] = []
    warnings: list[str] = []
    check(tmp_path, errors, warnings)
    assert not errors
    assert not warnings
