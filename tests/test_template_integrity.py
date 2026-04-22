"""Tests that tier templates on disk are internally consistent.

Separate from tests/test_cli.py (which tests the runtime CLI) — these
tests assert properties of the template bundles themselves.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_TEMPLATES = _REPO_ROOT / "src" / "agent_sdd" / "templates"


def test_all_four_tier_dirs_exist() -> None:
    for n in range(4):
        assert (_TEMPLATES / f"tier-{n}").is_dir(), f"missing tier-{n} template dir"


@pytest.mark.parametrize("tier", [0, 1, 2, 3])
def test_every_tier_has_agents_md(tier: int) -> None:
    assert (_TEMPLATES / f"tier-{tier}" / "AGENTS.md").is_file()


def test_dev_process_byte_equal_to_canonical() -> None:
    """tier-1/docs/development-process.md must be byte-identical to repo's own."""
    canon = _REPO_ROOT / "docs" / "development-process.md"
    tmpl = _TEMPLATES / "tier-1" / "docs" / "development-process.md"
    assert canon.read_bytes() == tmpl.read_bytes()


@pytest.mark.parametrize("tier", [1, 2, 3])
def test_tier_agents_md_contains_expected_markers(tier: int) -> None:
    agents_md = (_TEMPLATES / f"tier-{tier}" / "AGENTS.md").read_text(encoding="utf-8")
    assert "<!-- agent-sdd:begin:plan-before-build -->" in agents_md
    assert "<!-- agent-sdd:end:plan-before-build -->" in agents_md
    if tier >= 2:
        assert "<!-- agent-sdd:begin:spec-before-design -->" in agents_md
        assert "<!-- agent-sdd:end:spec-before-design -->" in agents_md


def test_tier_0_agents_md_has_no_gate_markers() -> None:
    agents_md = (_TEMPLATES / "tier-0" / "AGENTS.md").read_text(encoding="utf-8")
    assert "<!-- agent-sdd:begin:" not in agents_md
    assert "<!-- agent-sdd:end:" not in agents_md


def test_agents_md_section_fragments_exist() -> None:
    fragments_dir = _TEMPLATES / "agents-md-sections"
    for name in ["plan-before-build.md", "spec-before-design.md"]:
        assert (fragments_dir / name).is_file()


def test_harnesses_yaml_is_valid() -> None:
    import yaml
    data = yaml.safe_load((_TEMPLATES / "harnesses.yaml").read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) >= 5  # at least Claude, Cursor, Copilot, Windsurf, Kiro
    for entry in data:
        assert "path" in entry
        assert "body" in entry
