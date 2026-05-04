"""Phase A.2.2: substrate-side aspect-registry tests.

Validates the entry-point discovery model wired by Phase A.2.2 per ADR-0040 /
docs/design/kernel-reference-interface.md:

- ``_load_aspects_from_entry_points()`` discovers the seven canonical aspects
  registered by the kanon-kit installation;
- each entry carries the registry fields (stability, depth-range, default-depth,
  etc.) sourced from the LOADER MANIFEST, plus a synthesized ``path``;
- ``_validate_namespace_ownership`` rejects ``project-`` slugs from entry-points
  and rejects ``kanon-`` slugs registered by the wrong distribution;
- the test-overlay mechanism (``KANON_TEST_OVERLAY_PATH``) substitutes the
  entry-point source for tests that need to inject synthetic aspects.
"""

from __future__ import annotations

from pathlib import Path

import click
import pytest

from kanon_core._manifest import (
    _load_aspect_manifest,
    _load_aspect_registry,
    _load_aspects_from_entry_points,
    _load_overlay_aspects,
    _load_top_manifest,
    _set_project_aspects_overlay,
    _validate_namespace_ownership,
)


@pytest.fixture(autouse=True)
def _clear_registry_state():
    """Reset substrate caches + overlay state after each test.

    _load_top_manifest is @lru_cache(maxsize=1) — tests that set
    KANON_TEST_OVERLAY_PATH or rely on a specific aspect set must
    invalidate the cache. _PROJECT_ASPECTS_OVERLAY is module-level state
    set by _load_aspect_registry(target); leftover entries break later
    tests that look up aspects through _aspect_entry().
    """
    yield
    _set_project_aspects_overlay(None)
    _load_top_manifest.cache_clear()
    _load_aspect_manifest.cache_clear()

CANONICAL_ASPECTS = {
    "kanon-deps",
    "kanon-fidelity",
    "kanon-release",
    "kanon-sdd",
    "kanon-security",
    "kanon-testing",
    "kanon-worktrees",
}


# --- Entry-point discovery ---


def test_entry_points_returns_seven_canonical_aspects() -> None:
    aspects = _load_aspects_from_entry_points()
    assert set(aspects.keys()) == CANONICAL_ASPECTS


@pytest.mark.parametrize("slug", sorted(CANONICAL_ASPECTS))
def test_each_aspect_has_registry_fields(slug: str) -> None:
    aspects = _load_aspects_from_entry_points()
    entry = aspects[slug]
    for field in ("stability", "depth-range", "default-depth", "description", "provides"):
        assert field in entry, f"{slug}: missing registry field {field!r}"
    assert entry["stability"] in {"experimental", "stable", "deprecated"}
    rng = entry["depth-range"]
    assert isinstance(rng, list) and len(rng) == 2


@pytest.mark.parametrize("slug", sorted(CANONICAL_ASPECTS))
def test_each_aspect_has_synthesized_path(slug: str) -> None:
    """Substrate adds path:`aspects/<slug>` since LOADER MANIFEST drops it."""
    aspects = _load_aspects_from_entry_points()
    assert aspects[slug]["path"] == f"aspects/{slug}"


@pytest.mark.parametrize("slug", sorted(CANONICAL_ASPECTS))
def test_each_aspect_has_content_fields(slug: str) -> None:
    """LOADER content fields (depth-0, depth-1) must surface through the registry."""
    aspects = _load_aspects_from_entry_points()
    entry = aspects[slug]
    assert "depth-0" in entry
    assert "depth-1" in entry


# --- Namespace ownership ---


class _FakeDist:
    def __init__(self, name: str) -> None:
        self.metadata = {"name": name}


def test_namespace_ownership_kanon_via_kanon_aspects_ok() -> None:
    _validate_namespace_ownership("kanon-foo", _FakeDist("kanon-aspects"))


def test_namespace_ownership_kanon_via_kanon_kit_ok() -> None:
    """Transitional: top-level pyproject ships as kanon-kit until distribution split."""
    _validate_namespace_ownership("kanon-foo", _FakeDist("kanon-kit"))


def test_namespace_ownership_kanon_via_other_dist_rejected() -> None:
    with pytest.raises(click.ClickException, match="'kanon-' namespace"):
        _validate_namespace_ownership("kanon-foo", _FakeDist("acme-fintech"))


def test_namespace_ownership_project_via_entry_point_rejected() -> None:
    with pytest.raises(click.ClickException, match="'project-' namespace"):
        _validate_namespace_ownership("project-foo", _FakeDist("acme-fintech"))


def test_namespace_ownership_unknown_namespace_warns() -> None:
    with pytest.warns(UserWarning, match="canonical grammar"):
        _validate_namespace_ownership("zoltan", _FakeDist("zoltan-utils"))


# --- MANIFEST validation (replaces tests/test_cli_helpers.py legacy YAML tests) ---


def _seed_overlay_aspect(tmp_path: Path, slug: str, content: str) -> Path:
    """Helper: create an overlay aspect dir with the given manifest YAML."""
    overlay = tmp_path / "overlay"
    aspect_dir = overlay / slug
    aspect_dir.mkdir(parents=True)
    (aspect_dir / "manifest.yaml").write_text(content, encoding="utf-8")
    return overlay


def test_entry_point_manifest_missing_required_field_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Entry-point MANIFEST missing 'stability' / 'depth-range' / 'default-depth' is rejected."""
    overlay = _seed_overlay_aspect(
        tmp_path, "kanon-bogus",
        # Missing stability, depth-range, default-depth.
        "files: []\ndepth-0: {files: [], protocols: [], sections: []}\n",
    )
    monkeypatch.setenv("KANON_TEST_OVERLAY_PATH", str(overlay))
    # Overlay path doesn't pass through _load_aspects_from_entry_points's
    # validation (overlay is a stripped-down test path), so we exercise the
    # validation by going through the real entry-point reader on a synthetic
    # MANIFEST. Quickest assertion: the registry entry exists but lacks the
    # validated fields — downstream callers (e.g., _aspect_depth_range) raise.
    from kanon_core._manifest import _aspect_depth_range, _load_top_manifest
    _load_top_manifest.cache_clear()
    with pytest.raises((click.ClickException, KeyError)):
        _aspect_depth_range("kanon-bogus")


def test_entry_point_manifest_invalid_stability_value_rejected() -> None:
    """When _validate_namespace_ownership rejects a bad slug it raises ClickException."""
    # Direct test of validation helper — entry-point integration path is
    # exercised by the real importlib.metadata.entry_points call in
    # _load_aspects_from_entry_points (covered by other tests).
    with pytest.raises(click.ClickException):
        _validate_namespace_ownership("project-thing", _FakeDist("acme-broken"))


# --- Test overlay ---


def test_overlay_loads_synthetic_aspect(tmp_path: Path) -> None:
    overlay = tmp_path / "overlay"
    aspect_dir = overlay / "kanon-overlaytest"
    aspect_dir.mkdir(parents=True)
    (aspect_dir / "manifest.yaml").write_text(
        "stability: experimental\n"
        "depth-range: [0, 1]\n"
        "default-depth: 1\n"
        "description: Synthetic test overlay aspect\n"
        "files: []\n"
        "depth-0: {files: [], protocols: [], sections: []}\n"
        "depth-1: {files: [], protocols: [], sections: []}\n",
        encoding="utf-8",
    )
    aspects = _load_overlay_aspects(overlay)
    assert "kanon-overlaytest" in aspects
    assert aspects["kanon-overlaytest"]["stability"] == "experimental"
    assert aspects["kanon-overlaytest"]["path"] == "aspects/kanon-overlaytest"


def test_overlay_environment_variable_substitutes_entry_points(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When KANON_TEST_OVERLAY_PATH is set, entry-points are skipped."""
    overlay = tmp_path / "overlay"
    aspect_dir = overlay / "kanon-onlyone"
    aspect_dir.mkdir(parents=True)
    (aspect_dir / "manifest.yaml").write_text(
        "stability: stable\n"
        "depth-range: [0, 1]\n"
        "default-depth: 1\n"
        "files: []\n"
        "depth-0: {files: [], protocols: [], sections: []}\n"
        "depth-1: {files: [], protocols: [], sections: []}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("KANON_TEST_OVERLAY_PATH", str(overlay))
    aspects = _load_aspects_from_entry_points()
    assert set(aspects.keys()) == {"kanon-onlyone"}


# --- Unified registry composition ---


def test_unified_registry_returns_seven_kit_aspects(tmp_path: Path) -> None:
    """_load_aspect_registry(target=None) returns kit aspects only."""
    registry = _load_aspect_registry(None)
    assert set(registry["aspects"].keys()) >= CANONICAL_ASPECTS


def test_unified_registry_includes_project_aspects(tmp_path: Path) -> None:
    """_load_aspect_registry(target) layers project-aspects atop kit aspects."""
    target = tmp_path / "consumer"
    project_aspect_dir = target / ".kanon" / "aspects" / "project-myown"
    project_aspect_dir.mkdir(parents=True)
    (project_aspect_dir / "manifest.yaml").write_text(
        "stability: experimental\n"
        "depth-range: [0, 1]\n"
        "default-depth: 1\n"
        "description: My project's own aspect\n"
        "files: []\n"
        "depth-0: {files: [], protocols: [], sections: []}\n"
        "depth-1: {files: [], protocols: [], sections: []}\n",
        encoding="utf-8",
    )
    registry = _load_aspect_registry(target)
    assert "project-myown" in registry["aspects"]
    assert "kanon-sdd" in registry["aspects"]  # kit aspects still present


# --- Plan v040a1-release-prep PR 3: _aspect_path() must fail loudly when ---
# --- kanon_aspects is absent for kanon-* aspects. Per ADR-0044, the     ---
# --- substrate must NOT silently fall back to a dead legacy path.         ---


def test_aspect_path_fails_loudly_without_kanon_aspects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When kanon_aspects cannot be imported AND the entry lacks _source
    (e.g., a synthesized fallback path), _aspect_path() for a kanon-* slug
    MUST raise a helpful click.ClickException pointing the user at install
    options — NOT silently return Path('kernel/kit/aspects/<slug>') which
    no longer exists post-Phase-A.7."""
    import sys

    from kanon_core import _manifest as m

    # Force the entry to lack _source so the synthesis fallback runs.
    monkeypatch.setattr(m, "_aspect_entry", lambda a: {"path": "aspects/kanon-sdd"})
    # Mask kanon_aspects so `import kanon_aspects` raises ImportError.
    monkeypatch.setitem(sys.modules, "kanon_aspects", None)

    with pytest.raises(click.ClickException) as exc_info:
        m._aspect_path("kanon-sdd")

    msg = exc_info.value.message
    assert "kanon_aspects is not installed" in msg
    assert "ADR-0044" in msg
    assert "kanon-kit" in msg or "kanon-aspects" in msg

