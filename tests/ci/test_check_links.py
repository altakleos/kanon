"""Tests for ci/check_links.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def mod(load_ci_script):
    return load_ci_script("check_links.py")


def test_real_repo_passes(mod, repo_root) -> None:
    """The kanon repo's own docs/ must have no broken links."""
    errors = mod.check_links(repo_root / "docs")
    assert errors == [], "broken links found:\n  " + "\n  ".join(errors)


def test_main_exits_zero_on_ok(mod, repo_root, capsys: pytest.CaptureFixture[str]) -> None:
    rc = mod.main(["--root", str(repo_root / "docs")])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["status"] == "ok"


def test_broken_link_detected(mod, tmp_path: Path) -> None:
    (tmp_path / "test.md").write_text(
        "[broken](./nonexistent.md)\n", encoding="utf-8"
    )
    errors = mod.check_links(tmp_path)
    assert len(errors) > 0
    assert "nonexistent.md" in errors[0]


def test_external_links_skipped(mod, tmp_path: Path) -> None:
    (tmp_path / "test.md").write_text(
        "[ext](https://example.com)\n", encoding="utf-8"
    )
    errors = mod.check_links(tmp_path)
    assert errors == []


def test_code_block_links_skipped(mod, tmp_path: Path) -> None:
    (tmp_path / "test.md").write_text(
        "```\n[link](./missing.md)\n```\n", encoding="utf-8"
    )
    errors = mod.check_links(tmp_path)
    assert errors == []
