"""Tests for ci/check_foundations.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def mod(load_ci_script):
    return load_ci_script("check_foundations.py")


def test_real_repo_passes(mod, repo_root) -> None:
    """The kanon repo itself must pass foundation checks."""
    errors, _warnings = mod.check(
        repo_root / "docs" / "foundations",
        repo_root / "docs" / "specs",
    )
    assert errors == [], "check_foundations failed:\n  " + "\n  ".join(errors)


def test_main_exits_zero_on_ok(mod, repo_root, capsys: pytest.CaptureFixture[str]) -> None:
    rc = mod.main([
        "--foundations", str(repo_root / "docs" / "foundations"),
        "--specs", str(repo_root / "docs" / "specs"),
    ])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["status"] == "ok"


def test_missing_foundation_ref(mod, tmp_path: Path) -> None:
    """A spec referencing a non-existent foundation slug should error."""
    foundations = tmp_path / "foundations"
    foundations.mkdir()
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "bad-spec.md").write_text(
        "---\nserves:\n  - nonexistent-slug\nstatus: deferred\n---\n# Bad\n",
        encoding="utf-8",
    )
    errors, _ = mod.check(foundations, specs)
    assert len(errors) > 0
    assert "nonexistent-slug" in errors[0]


def test_invalid_principle_kind(mod, tmp_path: Path) -> None:
    """A principle with an invalid kind should error."""
    foundations = tmp_path / "foundations"
    foundations.mkdir()
    principles = foundations / "principles"
    principles.mkdir()
    (principles / "bad.md").write_text(
        "---\nid: bad-principle\nkind: invalid\nstatus: accepted\n---\n# Bad\n",
        encoding="utf-8",
    )
    specs = tmp_path / "specs"
    specs.mkdir()
    errors, _ = mod.check(foundations, specs)
    assert len(errors) > 0
    assert "invalid" in errors[0]


def test_superseded_spec_exempt_from_fixtures_check(mod, tmp_path: Path) -> None:
    """A superseded spec with `realizes:` but no `fixtures:`/`fixtures_deferred:`
    is exempt — its contract has been replaced by another spec, so requiring
    fixtures would be wrong (the fixtures, if any, live in the replacement).
    Mirrors the existing exemption for status: deferred.
    """
    foundations = tmp_path / "foundations"
    foundations.mkdir()
    principles = foundations / "principles"
    principles.mkdir()
    (principles / "P-foo.md").write_text(
        "---\nid: P-foo\nkind: pedagogical\nstatus: accepted\n---\n# P-foo\n",
        encoding="utf-8",
    )
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "old-umbrella.md").write_text(
        "---\nstatus: superseded\nrealizes:\n  - P-foo\nsuperseded-by:\n  - docs/specs/new.md\n---\n# Old umbrella\n",
        encoding="utf-8",
    )
    errors, _ = mod.check(foundations, specs)
    # No fixtures rule violation despite `realizes:` + no `fixtures:`/`fixtures_deferred:`.
    assert not any("'fixtures:'" in e for e in errors), errors


def test_orphan_exempt_requires_reason(mod, tmp_path: Path) -> None:
    """Per spec-graph-orphans INV-5, `orphan-exempt: true` MUST pair
    with a non-empty `orphan-exempt-reason:`. Missing reason is an error."""
    foundations = tmp_path / "foundations"
    foundations.mkdir()
    principles = foundations / "principles"
    principles.mkdir()
    (principles / "P-bare.md").write_text(
        "---\nid: P-bare\nkind: pedagogical\nstatus: accepted\n"
        "orphan-exempt: true\n---\n# P-bare\n",
        encoding="utf-8",
    )
    specs = tmp_path / "specs"
    specs.mkdir()
    errors, _ = mod.check(foundations, specs)
    assert any("orphan-exempt-reason" in e for e in errors), errors


def test_orphan_exempt_with_reason_passes(mod, tmp_path: Path) -> None:
    foundations = tmp_path / "foundations"
    foundations.mkdir()
    principles = foundations / "principles"
    principles.mkdir()
    (principles / "P-conduct.md").write_text(
        "---\nid: P-conduct\nkind: pedagogical\nstatus: accepted\n"
        "orphan-exempt: true\norphan-exempt-reason: agent stance\n---\n",
        encoding="utf-8",
    )
    specs = tmp_path / "specs"
    specs.mkdir()
    errors, _ = mod.check(foundations, specs)
    assert not any("orphan-exempt" in e for e in errors), errors


def test_orphan_exempt_empty_reason_fails(mod, tmp_path: Path) -> None:
    """Whitespace-only or empty reason strings are rejected."""
    foundations = tmp_path / "foundations"
    foundations.mkdir()
    principles = foundations / "principles"
    principles.mkdir()
    (principles / "P-bare.md").write_text(
        "---\nid: P-bare\nkind: pedagogical\nstatus: accepted\n"
        "orphan-exempt: true\norphan-exempt-reason: '   '\n---\n",
        encoding="utf-8",
    )
    specs = tmp_path / "specs"
    specs.mkdir()
    errors, _ = mod.check(foundations, specs)
    assert any("orphan-exempt-reason" in e for e in errors), errors


def test_deferred_spec_still_exempt_from_fixtures_check(mod, tmp_path: Path) -> None:
    """Regression: extending the exemption to `superseded` must NOT remove
    the existing `deferred` exemption."""
    foundations = tmp_path / "foundations"
    foundations.mkdir()
    principles = foundations / "principles"
    principles.mkdir()
    (principles / "P-bar.md").write_text(
        "---\nid: P-bar\nkind: pedagogical\nstatus: accepted\n---\n# P-bar\n",
        encoding="utf-8",
    )
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "future-thing.md").write_text(
        "---\nstatus: deferred\nrealizes:\n  - P-bar\n---\n# Future\n",
        encoding="utf-8",
    )
    errors, _ = mod.check(foundations, specs)
    assert not any("'fixtures:'" in e for e in errors), errors
