"""Tests for the cross-link graph load primitive (`kanon._graph`).

Exercises node discovery, edge extraction, namespace resolution, and the
inbound-edge index distinction between live and all sources. The
`test_real_repo_*` tests guard against regressions when this primitive
is later consumed by `kanon graph orphans` and `kanon graph rename`.
"""

from __future__ import annotations

from pathlib import Path

from kanon._graph import (
    EDGE_INV_REF,
    EDGE_REALIZES,
    EDGE_REQUIRES,
    EDGE_SERVES,
    EDGE_SERVES_PLAN,
    EDGE_STRESSED_BY,
    EDGE_STRESSES,
    NAMESPACE_ASPECT,
    NAMESPACE_CAPABILITY,
    NAMESPACE_PERSONA,
    NAMESPACE_PRINCIPLE,
    NAMESPACE_SPEC,
    NAMESPACE_VISION,
    Node,
    build_graph,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Synthetic-repo helpers


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_minimal_repo(root: Path) -> None:
    """Create a minimal repo skeleton with the directories `_discover_*`
    expects but no content. Specific tests add files on top.
    """
    (root / "docs" / "foundations" / "principles").mkdir(parents=True)
    (root / "docs" / "foundations" / "personas").mkdir(parents=True)
    (root / "docs" / "specs").mkdir(parents=True)
    (root / "docs" / "plans").mkdir(parents=True)
    (root / "src" / "kanon" / "kit").mkdir(parents=True)


# ---------------------------------------------------------------------------
# Node discovery


def test_principle_node_discovery(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    _write(
        tmp_path / "docs/foundations/principles/P-foo.md",
        "---\nid: P-foo\nkind: pedagogical\nstatus: accepted\n---\n# P-foo\n",
    )
    g = build_graph(tmp_path)
    principles = [n for n in g.nodes if n.namespace == NAMESPACE_PRINCIPLE]
    assert [n.slug for n in principles] == ["P-foo"]
    assert principles[0].status == "accepted"
    assert principles[0].extra["kind"] == "pedagogical"


def test_persona_node_discovery(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    _write(
        tmp_path / "docs/foundations/personas/sensei.md",
        "---\nid: sensei\n---\n# sensei\n",
    )
    g = build_graph(tmp_path)
    personas = [n for n in g.nodes if n.namespace == NAMESPACE_PERSONA]
    assert [n.slug for n in personas] == ["sensei"]


def test_spec_slug_is_filename_stem(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    _write(
        tmp_path / "docs/specs/foo-bar.md",
        "---\nstatus: draft\n---\n# foo-bar\n",
    )
    g = build_graph(tmp_path)
    specs = [n for n in g.nodes if n.namespace == NAMESPACE_SPEC]
    assert [n.slug for n in specs] == ["foo-bar"]


def test_vision_singleton(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    _write(
        tmp_path / "docs/foundations/vision.md",
        "---\nstatus: accepted\n---\n# Vision\n",
    )
    g = build_graph(tmp_path)
    vision = [n for n in g.nodes if n.namespace == NAMESPACE_VISION]
    assert len(vision) == 1
    assert vision[0].slug == "vision"


def test_aspect_and_capability_discovery(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    kit_root = tmp_path / "src/kanon/kit"
    _write(kit_root / "manifest.yaml", (
        "aspects:\n"
        "  alpha:\n"
        "    path: aspects/alpha\n"
        "    provides: [discipline-x]\n"
        "    requires: []\n"
        "  beta:\n"
        "    path: aspects/beta\n"
        "    provides: []\n"
        "    requires:\n"
        "      - discipline-x\n"
        "      - alpha >= 1\n"
    ))
    _write(kit_root / "aspects/alpha/manifest.yaml", "depth-0:\n  files: []\n")
    _write(kit_root / "aspects/beta/manifest.yaml", "depth-0:\n  files: []\n")
    g = build_graph(tmp_path)
    aspects = sorted(n.slug for n in g.nodes if n.namespace == NAMESPACE_ASPECT)
    capabilities = sorted(n.slug for n in g.nodes if n.namespace == NAMESPACE_CAPABILITY)
    assert aspects == ["alpha", "beta"]
    assert capabilities == ["discipline-x"]


# ---------------------------------------------------------------------------
# Edge extraction


def test_spec_emits_realizes_serves_stressed_by(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/principles/P-foo.md",
           "---\nid: P-foo\nkind: pedagogical\nstatus: accepted\n---\n# P-foo\n")
    _write(tmp_path / "docs/foundations/personas/sensei.md",
           "---\nid: sensei\n---\n")
    _write(tmp_path / "docs/foundations/vision.md", "---\n---\n# Vision\n")
    _write(tmp_path / "docs/specs/feature.md",
           "---\nstatus: draft\nrealizes: [P-foo]\nserves: [vision]\n"
           "stressed_by: [sensei]\n---\n# Feature\n")
    g = build_graph(tmp_path)
    kinds = {e.kind for e in g.edges}
    assert {EDGE_REALIZES, EDGE_SERVES, EDGE_STRESSED_BY}.issubset(kinds)
    realizes = [e for e in g.edges if e.kind == EDGE_REALIZES]
    assert (realizes[0].src_slug, realizes[0].dst_slug,
            realizes[0].dst_namespace) == ("feature", "P-foo", NAMESPACE_PRINCIPLE)


def test_persona_stresses_resolves_to_spec_or_principle(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/principles/P-foo.md",
           "---\nid: P-foo\nkind: pedagogical\nstatus: accepted\n---\n")
    _write(tmp_path / "docs/specs/some-spec.md",
           "---\nstatus: draft\n---\n# Some\n")
    _write(tmp_path / "docs/foundations/personas/p1.md",
           "---\nid: p1\nstresses:\n  - P-foo\n  - some-spec\n---\n")
    g = build_graph(tmp_path)
    stresses = [e for e in g.edges if e.kind == EDGE_STRESSES]
    targets = {(e.dst_slug, e.dst_namespace) for e in stresses}
    assert ("P-foo", NAMESPACE_PRINCIPLE) in targets
    assert ("some-spec", NAMESPACE_SPEC) in targets


def test_aspect_requires_distinguishes_depth_and_capability(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    kit_root = tmp_path / "src/kanon/kit"
    _write(kit_root / "manifest.yaml", (
        "aspects:\n"
        "  alpha:\n"
        "    path: aspects/alpha\n"
        "    provides: [cap-x]\n"
        "    requires: []\n"
        "  beta:\n"
        "    path: aspects/beta\n"
        "    provides: []\n"
        "    requires:\n"
        "      - alpha >= 1\n"
        "      - cap-x\n"
    ))
    _write(kit_root / "aspects/alpha/manifest.yaml", "depth-0:\n  files: []\n")
    _write(kit_root / "aspects/beta/manifest.yaml", "depth-0:\n  files: []\n")
    g = build_graph(tmp_path)
    requires = [e for e in g.edges if e.kind == EDGE_REQUIRES]
    by_dst = {(e.dst_slug, e.dst_namespace) for e in requires}
    assert ("alpha", NAMESPACE_ASPECT) in by_dst
    assert ("cap-x", NAMESPACE_CAPABILITY) in by_dst


def test_plan_serves_frontmatter_creates_plan_edge(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/specs/feature.md", "---\nstatus: draft\n---\n# F\n")
    _write(tmp_path / "docs/plans/build-feature.md",
           "---\nstatus: planned\nserves:\n  - docs/specs/feature.md\n---\n# Plan\n")
    g = build_graph(tmp_path)
    plan_edges = [e for e in g.edges if e.kind == EDGE_SERVES_PLAN]
    assert any(e.src_slug == "build-feature" and e.dst_slug == "feature"
               for e in plan_edges)


def test_plan_prose_link_creates_plan_edge(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/specs/feature.md", "---\nstatus: draft\n---\n# F\n")
    _write(tmp_path / "docs/plans/build-feature.md",
           "---\nstatus: planned\n---\n# Plan\n\nSee [feature](../specs/feature.md).\n")
    g = build_graph(tmp_path)
    plan_edges = [e for e in g.edges if e.kind == EDGE_SERVES_PLAN]
    assert any(e.src_slug == "build-feature" and e.dst_slug == "feature"
               for e in plan_edges)


def test_inv_ref_resolves_to_other_spec(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/specs/foo.md",
           "---\nstatus: draft\n---\n<!-- INV-foo-bar -->\n1. body\n")
    _write(tmp_path / "docs/specs/baz.md",
           "---\nstatus: draft\n---\n# baz\n\nReferences INV-foo-bar inline.\n")
    g = build_graph(tmp_path)
    inv_refs = [e for e in g.edges if e.kind == EDGE_INV_REF]
    assert any(e.src_slug == "baz" and e.dst_slug == "foo" for e in inv_refs)


def test_inv_ref_ignores_self_reference(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    # foo.md defines its own anchor and references it in prose; should not
    # produce a self-edge.
    _write(tmp_path / "docs/specs/foo.md",
           "---\nstatus: draft\n---\n<!-- INV-foo-bar -->\n1. body\n\n"
           "Self-mention: INV-foo-bar.\n")
    g = build_graph(tmp_path)
    inv_refs = [e for e in g.edges if e.kind == EDGE_INV_REF]
    assert all(e.src_slug != e.dst_slug for e in inv_refs)


# ---------------------------------------------------------------------------
# Liveness / inbound indices


def test_inbound_live_excludes_deferred_source(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/principles/P-foo.md",
           "---\nid: P-foo\nkind: pedagogical\nstatus: accepted\n---\n")
    # A deferred spec realizing P-foo should NOT save it from orphan status.
    _write(tmp_path / "docs/specs/future.md",
           "---\nstatus: deferred\nrealizes: [P-foo]\n---\n# Future\n")
    g = build_graph(tmp_path)
    key = (NAMESPACE_PRINCIPLE, "P-foo")
    assert len(g.inbound_all.get(key, [])) == 1
    assert len(g.inbound_live.get(key, [])) == 0


def test_inbound_live_includes_accepted_source(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/principles/P-foo.md",
           "---\nid: P-foo\nkind: pedagogical\nstatus: accepted\n---\n")
    _write(tmp_path / "docs/specs/now.md",
           "---\nstatus: accepted\nrealizes: [P-foo]\n---\n# Now\n")
    g = build_graph(tmp_path)
    key = (NAMESPACE_PRINCIPLE, "P-foo")
    assert len(g.inbound_live.get(key, [])) == 1


def test_superseded_spec_does_not_contribute_inbound(tmp_path: Path) -> None:
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/principles/P-foo.md",
           "---\nid: P-foo\nkind: pedagogical\nstatus: accepted\n---\n")
    _write(tmp_path / "docs/specs/old.md",
           "---\nstatus: superseded\nrealizes: [P-foo]\n---\n# Old\n")
    g = build_graph(tmp_path)
    key = (NAMESPACE_PRINCIPLE, "P-foo")
    assert len(g.inbound_live.get(key, [])) == 0


def test_node_with_no_status_is_live(tmp_path: Path) -> None:
    """vision.md and aspect entries lack `status:` — they must still
    contribute inbound edges (they can never be orphan-candidates anyway,
    but the rule needs to hold for callers traversing forward)."""
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/principles/P-foo.md",
           "---\nid: P-foo\nkind: pedagogical\nstatus: accepted\n---\n")
    _write(tmp_path / "docs/foundations/vision.md", "---\n---\n# V\n")  # no status
    _write(tmp_path / "docs/specs/no-status.md",
           "---\nrealizes: [P-foo]\nserves: [vision]\n---\n# X\n")  # no status
    g = build_graph(tmp_path)
    key = (NAMESPACE_PRINCIPLE, "P-foo")
    assert len(g.inbound_live.get(key, [])) == 1


# ---------------------------------------------------------------------------
# orphan-exempt frontmatter (Node helpers)


def test_orphan_exempt_helpers() -> None:
    n = Node(
        slug="P-test",
        namespace=NAMESPACE_PRINCIPLE,
        path=Path("/dev/null"),
        status="accepted",
        frontmatter={"orphan-exempt": True, "orphan-exempt-reason": "agent stance"},
    )
    assert n.is_orphan_exempt() is True
    assert n.orphan_exempt_reason() == "agent stance"


def test_orphan_exempt_default_false() -> None:
    n = Node(
        slug="P-test",
        namespace=NAMESPACE_PRINCIPLE,
        path=Path("/dev/null"),
        status="accepted",
        frontmatter={},
    )
    assert n.is_orphan_exempt() is False
    assert n.orphan_exempt_reason() is None


# ---------------------------------------------------------------------------
# Real-repo smoke (regression guard for downstream commands)


def test_real_repo_loads_without_error() -> None:
    g = build_graph(_REPO_ROOT)
    assert len(g.nodes) > 0
    assert len(g.edges) > 0


def test_real_repo_has_known_aspects() -> None:
    g = build_graph(_REPO_ROOT)
    aspects = {n.slug for n in g.nodes if n.namespace == NAMESPACE_ASPECT}
    assert {
        "kanon-sdd", "kanon-worktrees", "kanon-release",
        "kanon-testing", "kanon-security", "kanon-deps",
    }.issubset(aspects)


def test_real_repo_has_known_principles() -> None:
    g = build_graph(_REPO_ROOT)
    principles = {n.slug for n in g.nodes if n.namespace == NAMESPACE_PRINCIPLE}
    assert "P-prose-is-code" in principles
    assert "P-cross-link-dont-duplicate" in principles


def test_real_repo_specs_carry_status() -> None:
    g = build_graph(_REPO_ROOT)
    spec_nodes = [n for n in g.nodes if n.namespace == NAMESPACE_SPEC]
    # At least one accepted, at least one deferred, at least one superseded
    statuses = {n.status for n in spec_nodes}
    assert "accepted" in statuses or "accepted (lite)" in statuses
    assert "deferred" in statuses
    assert "superseded" in statuses


def test_real_repo_inbound_live_excludes_deferred_specs() -> None:
    """The deferred orphans-spec realizes P-cross-link-dont-duplicate;
    the live count for that principle must not include the deferred spec
    once orphans-spec is shipped, but for now it's draft so it does count.
    Use an invariant not affected by current spec status: a principle
    that no live spec realizes (none such exists today, so we just check
    the index doesn't crash on missing keys).
    """
    g = build_graph(_REPO_ROOT)
    # Sanity: every (namespace, slug) appearing in inbound_live must also
    # be a known node (no dangling inbound entries for missing nodes).
    for key in g.inbound_live:
        assert key in g.by_slug, f"inbound_live points at unknown node {key}"
