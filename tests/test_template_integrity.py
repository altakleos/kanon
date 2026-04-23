"""Tests that the kit bundle on disk is internally consistent.

Separate from tests/test_cli.py (which tests the runtime CLI) — these
tests assert properties of the kit bundle itself.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]
_KIT = _REPO_ROOT / "src" / "kanon" / "kit"


def _load_manifest() -> dict:
    return yaml.safe_load((_KIT / "manifest.yaml").read_text(encoding="utf-8"))


def test_kit_root_has_expected_top_level_entries() -> None:
    for entry in ("manifest.yaml", "harnesses.yaml", "agents-md", "sections", "protocols", "files"):
        assert (_KIT / entry).exists(), f"missing kit entry: {entry}"


@pytest.mark.parametrize("tier", [0, 1, 2, 3])
def test_every_tier_has_agents_md_base(tier: int) -> None:
    assert (_KIT / "agents-md" / f"tier-{tier}.md").is_file()


def test_dev_process_byte_equal_to_canonical() -> None:
    """kit/files/docs/development-process.md must be byte-identical to repo's own."""
    canon = _REPO_ROOT / "docs" / "development-process.md"
    tmpl = _KIT / "files" / "docs" / "development-process.md"
    assert canon.read_bytes() == tmpl.read_bytes()


@pytest.mark.parametrize("tier", [1, 2, 3])
def test_tier_agents_md_contains_expected_markers(tier: int) -> None:
    agents_md = (_KIT / "agents-md" / f"tier-{tier}.md").read_text(encoding="utf-8")
    assert "<!-- kanon:begin:plan-before-build -->" in agents_md
    assert "<!-- kanon:end:plan-before-build -->" in agents_md
    if tier >= 2:
        assert "<!-- kanon:begin:spec-before-design -->" in agents_md
        assert "<!-- kanon:end:spec-before-design -->" in agents_md


def test_tier_0_agents_md_has_no_gate_markers() -> None:
    agents_md = (_KIT / "agents-md" / "tier-0.md").read_text(encoding="utf-8")
    assert "<!-- kanon:begin:" not in agents_md
    assert "<!-- kanon:end:" not in agents_md


def test_sections_fragments_exist() -> None:
    for name in ("plan-before-build.md", "spec-before-design.md"):
        assert (_KIT / "sections" / name).is_file()


def test_harnesses_yaml_is_valid() -> None:
    data = yaml.safe_load((_KIT / "harnesses.yaml").read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) >= 5  # at least Claude, Cursor, Copilot, Windsurf, Kiro
    for entry in data:
        assert "path" in entry
        assert "body" in entry


def test_manifest_parses_with_four_tiers() -> None:
    manifest = _load_manifest()
    for n in range(4):
        key = f"tier-{n}"
        assert key in manifest
        assert isinstance(manifest[key].get("files", []), list)
        assert isinstance(manifest[key].get("protocols", []), list)
    assert isinstance(manifest["agents-md-sections"], dict)


def test_manifest_paths_resolve() -> None:
    """Every path declared in manifest.yaml must resolve to an extant file."""
    manifest = _load_manifest()
    errors: list[str] = []
    for n in range(4):
        entry = manifest.get(f"tier-{n}", {})
        for rel in entry.get("files", []):
            p = _KIT / "files" / rel
            if not p.is_file():
                errors.append(f"tier-{n}.files references missing path: {rel}")
        for rel in entry.get("protocols", []):
            p = _KIT / "protocols" / rel
            if not p.is_file():
                errors.append(f"tier-{n}.protocols references missing path: {rel}")
    assert not errors, "\n".join(errors)
