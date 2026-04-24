"""Tests that the kit bundle on disk is internally consistent.

Separate from tests/test_cli.py (which tests the runtime CLI) — these
tests assert properties of the kit bundle itself under the aspect-model
layout (ADR-0012 / docs/design/aspect-model.md).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]
_KIT = _REPO_ROOT / "src" / "kanon" / "kit"
_SDD = _KIT / "aspects" / "sdd"


def _load_top_manifest() -> dict:
    return yaml.safe_load((_KIT / "manifest.yaml").read_text(encoding="utf-8"))


def _load_sdd_manifest() -> dict:
    return yaml.safe_load((_SDD / "manifest.yaml").read_text(encoding="utf-8"))


# --- top-level layout ---


def test_kit_root_has_expected_top_level_entries() -> None:
    for entry in ("manifest.yaml", "harnesses.yaml", "kit.md", "aspects"):
        assert (_KIT / entry).exists(), f"missing kit entry: {entry}"


def test_kit_aspects_dir_has_sdd() -> None:
    assert (_KIT / "aspects" / "sdd").is_dir()


def test_sdd_aspect_has_required_subdirs() -> None:
    for sub in ("agents-md", "sections", "protocols", "files", "manifest.yaml"):
        assert (_SDD / sub).exists(), f"missing under aspects/sdd/: {sub}"


@pytest.mark.parametrize("depth", [0, 1, 2, 3])
def test_every_sdd_depth_has_agents_md_base(depth: int) -> None:
    assert (_SDD / "agents-md" / f"depth-{depth}.md").is_file()


# --- byte-equality against repo canonicals ---


def test_dev_process_byte_equal_to_canonical() -> None:
    canon = _REPO_ROOT / "docs" / "development-process.md"
    tmpl = _SDD / "files" / "docs" / "development-process.md"
    assert canon.read_bytes() == tmpl.read_bytes()


# --- AGENTS.md base templates use namespaced markers ---


@pytest.mark.parametrize("depth", [1, 2, 3])
def test_depth_agents_md_contains_expected_markers(depth: int) -> None:
    agents_md = (_SDD / "agents-md" / f"depth-{depth}.md").read_text(encoding="utf-8")
    assert "<!-- kanon:begin:sdd/plan-before-build -->" in agents_md
    assert "<!-- kanon:end:sdd/plan-before-build -->" in agents_md
    if depth >= 2:
        assert "<!-- kanon:begin:sdd/spec-before-design -->" in agents_md
        assert "<!-- kanon:end:sdd/spec-before-design -->" in agents_md


def test_depth_0_agents_md_has_no_gate_markers() -> None:
    agents_md = (_SDD / "agents-md" / "depth-0.md").read_text(encoding="utf-8")
    assert "<!-- kanon:begin:" not in agents_md
    assert "<!-- kanon:end:" not in agents_md


def test_sections_fragments_exist() -> None:
    for name in ("plan-before-build.md", "spec-before-design.md"):
        assert (_SDD / "sections" / name).is_file()


# --- harnesses.yaml and kit.md ---


def test_harnesses_yaml_is_valid() -> None:
    data = yaml.safe_load((_KIT / "harnesses.yaml").read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) >= 5  # at least Claude, Cursor, Copilot, Windsurf, Kiro
    for entry in data:
        assert "path" in entry
        assert "body" in entry


def test_kit_md_has_placeholders() -> None:
    text = (_KIT / "kit.md").read_text(encoding="utf-8")
    assert "${sdd_depth}" in text
    assert "${project_name}" in text


def test_kit_md_renders_with_placeholders() -> None:
    import string as _string

    text = (_KIT / "kit.md").read_text(encoding="utf-8")
    rendered = _string.Template(text).safe_substitute(
        {"sdd_depth": "2", "project_name": "demo"}
    )
    assert "${sdd_depth}" not in rendered
    assert "${project_name}" not in rendered
    assert "**Tier:** 2" in rendered
    assert "demo" in rendered


# --- manifests (registry + per-aspect) ---


def test_top_manifest_is_aspect_registry() -> None:
    top = _load_top_manifest()
    assert "aspects" in top and isinstance(top["aspects"], dict)
    assert "sdd" in top["aspects"]
    sdd = top["aspects"]["sdd"]
    for field in ("path", "stability", "depth-range", "default-depth"):
        assert field in sdd, f"sdd missing {field}"
    assert sdd["stability"] in {"experimental", "stable", "deprecated"}


@pytest.mark.parametrize("depth", [0, 1, 2, 3])
def test_sdd_sub_manifest_has_expected_depths(depth: int) -> None:
    sub = _load_sdd_manifest()
    key = f"depth-{depth}"
    assert key in sub, f"sub-manifest missing {key}"
    assert isinstance(sub[key], dict)


def test_manifest_paths_resolve() -> None:
    """Every path declared in sdd's sub-manifest resolves to an extant file."""
    sub = _load_sdd_manifest()
    errors: list[str] = []
    for d in range(4):
        entry = sub.get(f"depth-{d}", {})
        for rel in entry.get("files", []) or []:
            p = _SDD / "files" / rel
            if not p.is_file():
                errors.append(f"depth-{d}.files: {rel} missing under aspects/sdd/files/")
        for rel in entry.get("protocols", []) or []:
            p = _SDD / "protocols" / rel
            if not p.is_file():
                errors.append(
                    f"depth-{d}.protocols: {rel} missing under aspects/sdd/protocols/"
                )
    assert not errors, "\n".join(errors)


# --- worktrees aspect ---

_WORKTREES = _KIT / "aspects" / "worktrees"


def _load_worktrees_manifest() -> dict:
    return yaml.safe_load((_WORKTREES / "manifest.yaml").read_text(encoding="utf-8"))


def test_kit_worktrees_aspect_dir_exists() -> None:
    assert _WORKTREES.is_dir()


@pytest.mark.parametrize("depth", [0, 1, 2])
def test_worktrees_manifest_has_expected_depths(depth: int) -> None:
    sub = _load_worktrees_manifest()
    key = f"depth-{depth}"
    assert key in sub, f"worktrees sub-manifest missing {key}"
    assert isinstance(sub[key], dict)


def test_worktrees_manifest_paths_resolve() -> None:
    """Every path declared in worktrees sub-manifest resolves to an extant file."""
    sub = _load_worktrees_manifest()
    errors: list[str] = []
    for d in range(3):
        entry = sub.get(f"depth-{d}", {})
        for rel in entry.get("files", []) or []:
            p = _WORKTREES / "files" / rel
            if not p.is_file():
                errors.append(f"depth-{d}.files: {rel} missing under aspects/worktrees/files/")
        for rel in entry.get("protocols", []) or []:
            p = _WORKTREES / "protocols" / rel
            if not p.is_file():
                errors.append(
                    f"depth-{d}.protocols: {rel} missing under aspects/worktrees/protocols/"
                )
        for name in entry.get("sections", []) or []:
            if name == "protocols-index":
                continue  # dynamically rendered
            p = _WORKTREES / "sections" / f"{name}.md"
            if not p.is_file():
                errors.append(
                    f"depth-{d}.sections: {name} missing under aspects/worktrees/sections/"
                )
    assert not errors, "\n".join(errors)


@pytest.mark.parametrize("depth", [0, 1, 2])
def test_worktrees_agents_md_exists_per_depth(depth: int) -> None:
    assert (_WORKTREES / "agents-md" / f"depth-{depth}.md").is_file()


def test_worktrees_depth_1_has_branch_hygiene_marker() -> None:
    text = (_WORKTREES / "agents-md" / "depth-1.md").read_text(encoding="utf-8")
    assert "<!-- kanon:begin:worktrees/branch-hygiene -->" in text
