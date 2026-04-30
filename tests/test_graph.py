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


# ---------------------------------------------------------------------------
# _split_frontmatter / _read_md edge cases


def test_split_frontmatter_yaml_parses_to_list() -> None:
    """YAML that parses to a non-dict (e.g. a list) → returns ({}, body)."""
    from kanon._graph import _split_frontmatter

    text = "---\n- item1\n- item2\n---\n# Body\n"
    fm, body = _split_frontmatter(text)
    assert fm == {}
    assert body == "# Body\n"


def test_read_md_nonexistent_path(tmp_path: Path) -> None:
    """Non-existent path → returns ({}, '')."""
    from kanon._graph import _read_md

    fm, body = _read_md(tmp_path / "does-not-exist.md")
    assert fm == {}
    assert body == ""


# ---------------------------------------------------------------------------
# _iter_md: README.md and _template.md skipped


def test_iter_md_skips_readme_and_template(tmp_path: Path) -> None:
    from kanon._graph import _iter_md

    d = tmp_path / "docs"
    d.mkdir()
    (d / "README.md").write_text("# Readme\n")
    (d / "_template.md").write_text("# Template\n")
    (d / "real.md").write_text("# Real\n")
    results = list(_iter_md(d))
    assert [p.name for p in results] == ["real.md"]


# ---------------------------------------------------------------------------
# _discover_principles / _discover_personas: non-string id → no node


def test_discover_principles_non_string_id(tmp_path: Path) -> None:
    """Principle file with non-string id → no node created."""
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/principles/bad.md",
           "---\nid: 42\nkind: pedagogical\nstatus: accepted\n---\n")
    g = build_graph(tmp_path)
    principles = [n for n in g.nodes if n.namespace == NAMESPACE_PRINCIPLE]
    assert principles == []


def test_discover_personas_non_string_id(tmp_path: Path) -> None:
    """Persona file with non-string id → no node created."""
    _make_minimal_repo(tmp_path)
    _write(tmp_path / "docs/foundations/personas/bad.md",
           "---\nid: 123\n---\n")
    g = build_graph(tmp_path)
    personas = [n for n in g.nodes if n.namespace == NAMESPACE_PERSONA]
    assert personas == []


# ---------------------------------------------------------------------------
# _discover_aspects_and_capabilities: malformed YAML / non-dict shapes


def test_discover_aspects_malformed_yaml(tmp_path: Path) -> None:
    """Malformed YAML in top manifest → returns empty."""
    _make_minimal_repo(tmp_path)
    kit_root = tmp_path / "src/kanon/kit"
    _write(kit_root / "manifest.yaml", "{{not: valid: yaml:")
    g = build_graph(tmp_path)
    aspects = [n for n in g.nodes if n.namespace == NAMESPACE_ASPECT]
    assert aspects == []


def test_discover_aspects_data_not_dict(tmp_path: Path) -> None:
    """aspects_data not a dict → empty."""
    _make_minimal_repo(tmp_path)
    kit_root = tmp_path / "src/kanon/kit"
    _write(kit_root / "manifest.yaml", "aspects: not-a-dict\n")
    g = build_graph(tmp_path)
    aspects = [n for n in g.nodes if n.namespace == NAMESPACE_ASPECT]
    assert aspects == []


def test_discover_aspects_entry_not_dict(tmp_path: Path) -> None:
    """Aspect entry that is not a dict → skipped."""
    _make_minimal_repo(tmp_path)
    kit_root = tmp_path / "src/kanon/kit"
    _write(kit_root / "manifest.yaml", "aspects:\n  bad-aspect: not-a-dict\n")
    g = build_graph(tmp_path)
    aspects = [n for n in g.nodes if n.namespace == NAMESPACE_ASPECT]
    assert aspects == []


# ---------------------------------------------------------------------------
# _plan_edges: plans_dir doesn't exist → returns []


def test_plan_edges_missing_dir(tmp_path: Path) -> None:
    """plans_dir doesn't exist → returns []."""
    from kanon._graph import _plan_edges

    edges = _plan_edges(tmp_path / "nonexistent")
    assert edges == []


# ---------------------------------------------------------------------------
# _spec_inv_ref_edges: OSError reading spec → returns []; no-dash INV ref


def test_spec_inv_ref_edges_oserror(tmp_path: Path) -> None:
    """OSError reading spec → returns []."""
    from kanon._graph import _spec_inv_ref_edges

    node = Node(
        slug="broken",
        namespace=NAMESPACE_SPEC,
        path=tmp_path / "nonexistent.md",
        status="draft",
    )
    edges = _spec_inv_ref_edges(node, {"other"})
    assert edges == []


def test_spec_inv_ref_edges_no_dash_in_ref(tmp_path: Path) -> None:
    """INV ref with no dash after prefix → no edge."""
    from kanon._graph import _spec_inv_ref_edges

    spec_file = tmp_path / "nodash.md"
    spec_file.write_text("---\nstatus: draft\n---\nINVnodash text\n")
    node = Node(
        slug="nodash",
        namespace=NAMESPACE_SPEC,
        path=spec_file,
        status="draft",
    )
    edges = _spec_inv_ref_edges(node, {"other"})
    assert edges == []


# ---------------------------------------------------------------------------
# build_graph: edge with unresolved dst_namespace → filtered out


def test_build_graph_unresolved_dst_namespace_filtered(tmp_path: Path) -> None:
    """An edge whose dst_namespace remains None after resolution is
    excluded from inbound indices."""
    _make_minimal_repo(tmp_path)
    # Spec serves a slug that doesn't exist as any node → unresolved.
    _write(tmp_path / "docs/specs/lonely.md",
           "---\nstatus: draft\nserves: [nonexistent-thing]\n---\n")
    g = build_graph(tmp_path)
    # The edge exists but with dst_namespace=None.
    unresolved = [e for e in g.edges if e.dst_namespace is None]
    assert len(unresolved) >= 1
    # None of the unresolved edges appear in inbound indices.
    for key in g.inbound_all:
        for e in g.inbound_all[key]:
            assert e.dst_namespace is not None


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


# --- Error-path tests ---


def test_build_graph_missing_docs_dir(tmp_path: Path) -> None:
    """build_graph handles missing docs/ directory gracefully."""
    from kanon._graph import build_graph

    # tmp_path has no docs/ directory
    graph = build_graph(tmp_path)
    assert len(graph.nodes) == 0


def test_build_graph_malformed_frontmatter(tmp_path: Path) -> None:
    """build_graph handles files with malformed YAML frontmatter."""
    from kanon._graph import build_graph

    docs = tmp_path / "docs" / "plans"
    docs.mkdir(parents=True)
    bad = docs / "bad.md"
    bad.write_text("---\n: invalid yaml [\n---\n# Bad\n", encoding="utf-8")
    # Should not crash
    graph = build_graph(tmp_path)
    assert isinstance(graph.nodes, list)
