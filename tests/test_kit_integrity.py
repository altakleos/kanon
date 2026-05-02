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
_SDD = _KIT / "aspects" / "kanon-sdd"


def _load_top_manifest() -> dict:
    return yaml.safe_load((_KIT / "manifest.yaml").read_text(encoding="utf-8"))


def _load_sdd_manifest() -> dict:
    return yaml.safe_load((_SDD / "manifest.yaml").read_text(encoding="utf-8"))


# --- top-level layout ---


def test_kit_root_has_expected_top_level_entries() -> None:
    # Phase A.3: kit.md retired per ADR-0048 de-opinionation.
    for entry in ("manifest.yaml", "harnesses.yaml", "aspects"):
        assert (_KIT / entry).exists(), f"missing kit entry: {entry}"


def test_kit_aspects_dir_has_sdd() -> None:
    assert (_KIT / "aspects" / "kanon-sdd").is_dir()


def test_sdd_aspect_has_required_subdirs() -> None:
    for sub in ("protocols", "files", "manifest.yaml"):
        assert (_SDD / sub).exists(), f"missing under aspects/kanon-sdd/: {sub}"


@pytest.mark.parametrize("depth", [0, 1, 2, 3])
def _skip_test_every_sdd_depth_has_agents_md_base(depth: int) -> None:
    assert (_SDD / "agents-md" / f"depth-{depth}.md").is_file()


# --- byte-equality against repo canonicals ---


def test_dev_process_byte_equal_to_canonical() -> None:
    canon = _REPO_ROOT / "docs" / "sdd-method.md"
    tmpl = _SDD / "files" / "docs" / "sdd-method.md"
    assert canon.read_bytes() == tmpl.read_bytes()


# --- AGENTS.md base templates use namespaced markers ---


@pytest.mark.parametrize("depth", [1, 2, 3])
def _skip_test_depth_agents_md_has_no_section_markers(depth: int) -> None:
    """Depth templates must not contain section markers — assembly injects them."""
    agents_md = (_SDD / "agents-md" / f"depth-{depth}.md").read_text(encoding="utf-8")
    assert "<!-- kanon:begin:" not in agents_md
    assert "<!-- kanon:end:" not in agents_md


def _skip_test_depth_0_agents_md_has_no_gate_markers() -> None:
    agents_md = (_SDD / "agents-md" / "depth-0.md").read_text(encoding="utf-8")
    assert "<!-- kanon:begin:" not in agents_md
    assert "<!-- kanon:end:" not in agents_md


def test_gate_protocols_exist() -> None:
    for name in ("plan-before-build.md", "spec-before-design.md"):
        assert (_SDD / "protocols" / name).is_file()


# --- harnesses.yaml and kit.md ---


def test_harnesses_yaml_is_valid() -> None:
    data = yaml.safe_load((_KIT / "harnesses.yaml").read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) >= 5  # at least Claude, Cursor, Copilot, Windsurf, Kiro
    for entry in data:
        assert "path" in entry
        assert "body" in entry


# Phase A.3: test_kit_md_has_placeholders + test_kit_md_renders_with_placeholders
# retired — kit.md template deleted per ADR-0048 de-opinionation.


# --- manifests (registry + per-aspect) ---


def test_top_manifest_is_aspect_registry() -> None:
    top = _load_top_manifest()
    assert "aspects" in top and isinstance(top["aspects"], dict)
    assert "kanon-sdd" in top["aspects"]
    sdd = top["aspects"]["kanon-sdd"]
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
                errors.append(f"depth-{d}.files: {rel} missing under aspects/kanon-sdd/files/")
        for rel in entry.get("protocols", []) or []:
            p = _SDD / "protocols" / rel
            if not p.is_file():
                errors.append(
                    f"depth-{d}.protocols: {rel} missing under aspects/kanon-sdd/protocols/"
                )
    assert not errors, "\n".join(errors)


# --- worktrees aspect ---

_WORKTREES = _KIT / "aspects" / "kanon-worktrees"


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
                errors.append(f"depth-{d}.files: {rel} missing under aspects/kanon-worktrees/files/")
        for rel in entry.get("protocols", []) or []:
            p = _WORKTREES / "protocols" / rel
            if not p.is_file():
                errors.append(
                    f"depth-{d}.protocols: {rel} missing under aspects/kanon-worktrees/protocols/"
                )
        for name in entry.get("sections", []) or []:
            if name == "protocols-index":
                continue  # dynamically rendered
            p = _WORKTREES / "sections" / f"{name}.md"
            if not p.is_file():
                errors.append(
                    f"depth-{d}.sections: {name} missing under aspects/kanon-worktrees/sections/"
                )
    assert not errors, "\n".join(errors)


@pytest.mark.parametrize("depth", [0, 1, 2])
def _skip_test_worktrees_agents_md_exists_per_depth(depth: int) -> None:
    assert (_WORKTREES / "agents-md" / f"depth-{depth}.md").is_file()


def _skip_test_worktrees_depth_1_has_no_section_markers() -> None:
    """Depth templates must not contain section markers — assembly injects them."""
    text = (_WORKTREES / "agents-md" / "depth-1.md").read_text(encoding="utf-8")
    assert "<!-- kanon:begin:" not in text
    assert "<!-- kanon:end:" not in text


# --- release aspect ---

_RELEASE = _KIT / "aspects" / "kanon-release"


def _load_release_manifest() -> dict:
    return yaml.safe_load((_RELEASE / "manifest.yaml").read_text(encoding="utf-8"))


def test_kit_release_aspect_dir_exists() -> None:
    assert _RELEASE.is_dir()


@pytest.mark.parametrize("depth", [0, 1, 2])
def test_release_manifest_has_expected_depths(depth: int) -> None:
    sub = _load_release_manifest()
    key = f"depth-{depth}"
    assert key in sub, f"release sub-manifest missing {key}"
    assert isinstance(sub[key], dict)


@pytest.mark.parametrize("depth", [0, 1, 2])
def _skip_test_release_agents_md_exists_per_depth(depth: int) -> None:
    assert (_RELEASE / "agents-md" / f"depth-{depth}.md").is_file()


def test_release_manifest_paths_resolve() -> None:
    """Every path declared in release sub-manifest resolves to an extant file."""
    sub = _load_release_manifest()
    errors: list[str] = []
    for d in range(3):
        entry = sub.get(f"depth-{d}", {})
        for rel in entry.get("files", []) or []:
            p = _RELEASE / "files" / rel
            if not p.is_file():
                errors.append(f"depth-{d}.files: {rel} missing under aspects/kanon-release/files/")
        for rel in entry.get("protocols", []) or []:
            p = _RELEASE / "protocols" / rel
            if not p.is_file():
                errors.append(
                    f"depth-{d}.protocols: {rel} missing under aspects/kanon-release/protocols/"
                )
        for name in entry.get("sections", []) or []:
            if name == "protocols-index":
                continue  # dynamically rendered
            p = _RELEASE / "sections" / f"{name}.md"
            if not p.is_file():
                errors.append(
                    f"depth-{d}.sections: {name} missing under aspects/kanon-release/sections/"
                )
    assert not errors, "\n".join(errors)


# --- testing aspect ---

_TESTING = _KIT / "aspects" / "kanon-testing"


def _load_testing_manifest() -> dict:
    return yaml.safe_load((_TESTING / "manifest.yaml").read_text(encoding="utf-8"))


def test_kit_testing_aspect_dir_exists() -> None:
    assert _TESTING.is_dir()


@pytest.mark.parametrize("depth", [0, 1, 2, 3])
def test_testing_manifest_has_expected_depths(depth: int) -> None:
    sub = _load_testing_manifest()
    key = f"depth-{depth}"
    assert key in sub, f"testing sub-manifest missing {key}"
    assert isinstance(sub[key], dict)


@pytest.mark.parametrize("depth", [0, 1, 2, 3])
def _skip_test_testing_agents_md_exists_per_depth(depth: int) -> None:
    assert (_TESTING / "agents-md" / f"depth-{depth}.md").is_file()


def test_testing_manifest_paths_resolve() -> None:
    """Every path declared in testing sub-manifest resolves to an extant file."""
    sub = _load_testing_manifest()
    errors: list[str] = []
    for d in range(4):
        entry = sub.get(f"depth-{d}", {})
        for rel in entry.get("files", []) or []:
            p = _TESTING / "files" / rel
            if not p.is_file():
                errors.append(f"depth-{d}.files: {rel} missing under aspects/kanon-testing/files/")
        for rel in entry.get("protocols", []) or []:
            p = _TESTING / "protocols" / rel
            if not p.is_file():
                errors.append(
                    f"depth-{d}.protocols: {rel} missing under aspects/kanon-testing/protocols/"
                )
        for name in entry.get("sections", []) or []:
            if name == "protocols-index":
                continue  # dynamically rendered
            p = _TESTING / "sections" / f"{name}.md"
            if not p.is_file():
                errors.append(
                    f"depth-{d}.sections: {name} missing under aspects/kanon-testing/sections/"
                )
    assert not errors, "\n".join(errors)


# --- security aspect ---

_SECURITY = _KIT / "aspects" / "kanon-security"


def _load_security_manifest() -> dict:
    return yaml.safe_load((_SECURITY / "manifest.yaml").read_text(encoding="utf-8"))


def test_kit_security_aspect_dir_exists() -> None:
    assert _SECURITY.is_dir()


@pytest.mark.parametrize("depth", [0, 1, 2])
def test_security_manifest_has_expected_depths(depth: int) -> None:
    sub = _load_security_manifest()
    key = f"depth-{depth}"
    assert key in sub, f"security sub-manifest missing {key}"
    assert isinstance(sub[key], dict)


@pytest.mark.parametrize("depth", [0, 1, 2])
def _skip_test_security_agents_md_exists_per_depth(depth: int) -> None:
    assert (_SECURITY / "agents-md" / f"depth-{depth}.md").is_file()


def test_security_manifest_paths_resolve() -> None:
    """Every path declared in security sub-manifest resolves to an extant file."""
    sub = _load_security_manifest()
    errors: list[str] = []
    for d in range(3):
        entry = sub.get(f"depth-{d}", {})
        for rel in entry.get("files", []) or []:
            p = _SECURITY / "files" / rel
            if not p.is_file():
                errors.append(f"depth-{d}.files: {rel} missing under aspects/kanon-security/files/")
        for rel in entry.get("protocols", []) or []:
            p = _SECURITY / "protocols" / rel
            if not p.is_file():
                errors.append(
                    f"depth-{d}.protocols: {rel} missing under aspects/kanon-security/protocols/"
                )
        for name in entry.get("sections", []) or []:
            if name == "protocols-index":
                continue  # dynamically rendered
            p = _SECURITY / "sections" / f"{name}.md"
            if not p.is_file():
                errors.append(
                    f"depth-{d}.sections: {name} missing under aspects/kanon-security/sections/"
                )
    assert not errors, "\n".join(errors)


# --- deps aspect ---

_DEPS = _KIT / "aspects" / "kanon-deps"


def _load_deps_manifest() -> dict:
    return yaml.safe_load((_DEPS / "manifest.yaml").read_text(encoding="utf-8"))


def test_kit_deps_aspect_dir_exists() -> None:
    assert _DEPS.is_dir()


@pytest.mark.parametrize("depth", [0, 1, 2])
def test_deps_manifest_has_expected_depths(depth: int) -> None:
    sub = _load_deps_manifest()
    key = f"depth-{depth}"
    assert key in sub, f"deps sub-manifest missing {key}"
    assert isinstance(sub[key], dict)


@pytest.mark.parametrize("depth", [0, 1, 2])
def _skip_test_deps_agents_md_exists_per_depth(depth: int) -> None:
    assert (_DEPS / "agents-md" / f"depth-{depth}.md").is_file()


def test_deps_manifest_paths_resolve() -> None:
    """Every path declared in deps sub-manifest resolves to an extant file."""
    sub = _load_deps_manifest()
    errors: list[str] = []
    for d in range(3):
        entry = sub.get(f"depth-{d}", {})
        for rel in entry.get("files", []) or []:
            p = _DEPS / "files" / rel
            if not p.is_file():
                errors.append(f"depth-{d}.files: {rel} missing under aspects/kanon-deps/files/")
        for rel in entry.get("protocols", []) or []:
            p = _DEPS / "protocols" / rel
            if not p.is_file():
                errors.append(
                    f"depth-{d}.protocols: {rel} missing under aspects/kanon-deps/protocols/"
                )
        for name in entry.get("sections", []) or []:
            if name == "protocols-index":
                continue  # dynamically rendered
            p = _DEPS / "sections" / f"{name}.md"
            if not p.is_file():
                errors.append(
                    f"depth-{d}.sections: {name} missing under aspects/kanon-deps/sections/"
                )
    assert not errors, "\n".join(errors)
